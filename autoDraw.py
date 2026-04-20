import os
import random
import shlex
import signal
import subprocess
import sys
import time
import threading
import queue
from datetime import datetime
from pathlib import Path


import gpiod
import gpiodevice
from gpiod.line import Bias, Direction, Edge

from PIL import Image
from inky.auto import auto

import gpiod
import gpiodevice
from gpiod.line import Bias, Direction, Edge

# Optional Inky display support
try:
    from inky.auto import auto
    from PIL import Image
    HAVE_INKY = True
except ImportError:
    HAVE_INKY = False


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

OUTPUT_DIR = Path("/home/rob/generated_images")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# These are the GPIO numbers used by Pimoroni's current 7-colour
# button example on Raspberry Pi 5.
# If your platform differs, check with: gpioinfo
BUTTONS = [5, 6, 16, 24]   # A, B, C, D
LABELS = ["A", "B", "C", "D"]

# Button assignments
BUTTON_NEXT = "A"   # button 1
BUTTON_PREV = "B"   # button 2

# Supported image file types
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

# Optional debounce
DEBOUNCE_SECONDS = 0.25

# How long to leave each image on screen before generating another one
DISPLAY_SECONDS = 120

# Stable Diffusion command template.
# Replace this with the exact command you already use.
#
# Available fields:
#   {prompt}      -> the generated prompt text
#   {output_file} -> the PNG file to write
#

SD_COMMAND_TEMPLATE = (
    '/home/rob/OnnxStream/src/build/sd '
    '--prompt "{prompt}" '
    '--models-path "/home/rob/Models" '
    '--output "{output_file}" '
    '--rpi-lowmem '
    '--steps 10'
)

# Optional negative prompt support
NEGATIVE_PROMPT = "blurry, distorted, low quality, duplicate, cropped"

# Set to True if your SD script supports a negative prompt option
USE_NEGATIVE_PROMPT = False

# If enabled, this text is appended to every prompt
GLOBAL_QUALITY_HINT = "high detail, beautiful composition"

# Avoid immediate repeats
RECENT_PROMPTS_TO_AVOID = 10


# ------------------------------------------------------------
# Prompt vocabularies
# ------------------------------------------------------------

PROMPT_BANKS = {
    "subject": [
        "a lonely lighthouse",
        "a Victorian greenhouse",
        "a steam train crossing a viaduct",
        "an ancient oak tree",
        "a moonlit city street",
        "a retro-futuristic robot",
#        "a mountain monastery",
#        "a glass observatory",
#        "a floating island",
#        "a mechanical owl",
        "a starship captain",
        "an old telephone",
        "a happy dog",
        "a horse",
        "an old camera",
        "a futuristic camera",
        "an old vending machine",
        "an old TV",
        "a cup of coffee",
        "an old style hat",
        "a football player",
        "a futuristic cruise ship",
        "an brass telescope",
        "an old style computer",
        "a bicycle",
        "a piano",
        "a circus act",
        "a busy market",
        "an old car",
        "a flying car",
        
        
    ],
    "style": [
        "ascii art",
        "oil painting",
        "watercolour illustration",
        "storybook art",
        "cinematic concept art",
        "retro poster art",
        "dreamlike surrealism",
        "detailed pencil drawing",
        "bold colored cartoon",
        "newspaper photograph",
        "fantasy illustration",
        "Japanese woodblock print style",
        "soft pastel painting"
    ],
    "lighting": [
        "golden hour lighting",
        "misty morning light",
        "dramatic sunset lighting",
        "moonlight",
        "soft diffused light",
        "stormy sky lighting",
        "candlelit atmosphere",
        "bright spring daylight",
        "fog with shafts of light",
        "twilight glow"
    ],
    "mood": [
        "peaceful",
        "melancholic",
        "mysterious",
        "uplifting",
        "haunting",
        "nostalgic",
        "epic",
        "playful",
        "quiet and reflective",
        "otherworldly"
    ],
    "detail": [
        "rich textures",
        "intricate details",
        "subtle colour palette",
        "layered depth",
        "fine brushwork",
        "highly detailed background",
        "delicate atmosphere",
        "beautiful contrast",
        "strong focal point",
        "carefully balanced composition"
    ],
    "environment": [
        "surrounded by wildflowers",
        "in a snowy landscape",
        "overlooking the sea",
        "in autumn woods",
        "inside a ruined cathedral",
        "among rolling hills",
        "above the clouds",
        "beside a still lake",
        "in a rain-soaked alley",
        "on a windswept cliff"
    ]
}

PROMPT_TEMPLATES = [
    "{subject}, {environment}, {style}, {lighting}, {mood}, {detail}",
    "{style} of {subject}, {environment}, {lighting}, {mood}, {detail}",
    "{subject} in {style}, {lighting}, {environment}, {mood}, {detail}",
]


# ------------------------------------------------------------
# Prompt generation
# ------------------------------------------------------------

recent_prompts = []


def choose(parts, used=None):
    """Choose one random item from a list."""
    return random.choice(parts)


def build_prompt():
    """Build a prompt from the prompt banks."""
    parts = {
        "subject": choose(PROMPT_BANKS["subject"]),
        "style": choose(PROMPT_BANKS["style"]),
        "lighting": choose(PROMPT_BANKS["lighting"]),
        "mood": choose(PROMPT_BANKS["mood"]),
        "detail": choose(PROMPT_BANKS["detail"]),
        "environment": choose(PROMPT_BANKS["environment"]),
    }

    template = random.choice(PROMPT_TEMPLATES)
    prompt = template.format(**parts)

    if GLOBAL_QUALITY_HINT:
        prompt = f"{prompt}, {GLOBAL_QUALITY_HINT}"

    return prompt


def build_non_repeating_prompt(max_attempts=20):
    """Try to avoid recent prompt duplicates."""
    global recent_prompts

    for _ in range(max_attempts):
        prompt = build_prompt()
        if prompt not in recent_prompts:
            recent_prompts.append(prompt)
            if len(recent_prompts) > RECENT_PROMPTS_TO_AVOID:
                recent_prompts.pop(0)
            return prompt

    # Fall back if all attempts collide
    prompt = build_prompt()
    recent_prompts.append(prompt)
    if len(recent_prompts) > RECENT_PROMPTS_TO_AVOID:
        recent_prompts.pop(0)
    return prompt


# ------------------------------------------------------------
# Stable Diffusion execution
# ------------------------------------------------------------

def generate_output_filename():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"image_{timestamp}.png"


def build_sd_command(prompt, output_file):
    if USE_NEGATIVE_PROMPT:
        cmd = (
            SD_COMMAND_TEMPLATE
            + f' --negative-prompt "{NEGATIVE_PROMPT}"'
        )
    else:
        cmd = SD_COMMAND_TEMPLATE

    return cmd.format(prompt=prompt.replace('"', '\\"'),
                      output_file=str(output_file))


def run_stable_diffusion(prompt, output_file, timeout=18000):
    """
    Run the Stable Diffusion command and wait for it to complete.
    Returns True on success.
    """
    cmd = build_sd_command(prompt, output_file)
    print(f"\n[SD] Prompt: {prompt}")
    print(f"[SD] Command: {cmd}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            timeout=timeout,
            capture_output=True,
            text=True
        )

        if result.stdout:
            print("[SD stdout]")
            print(result.stdout)

        if result.stderr:
            print("[SD stderr]")
            print(result.stderr)

        if result.returncode != 0:
            print(f"[ERROR] Stable Diffusion process failed with code {result.returncode}")
            return False

        if not output_file.exists():
            print(f"[ERROR] Expected output file was not created: {output_file}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("[ERROR] Stable Diffusion generation timed out")
        return False
    except Exception as ex:
        print(f"[ERROR] Failed to run Stable Diffusion: {ex}")
        return False


# ------------------------------------------------------------
# Inky display support
# ------------------------------------------------------------

def display_on_inky(image_path):
    """
    Display an image on the Inky Impression.
    This uses Pimoroni's Python library if installed.
    """
    if not HAVE_INKY:
        print("[WARN] Inky library not installed; skipping display")
        return

    try:
        inky = auto(ask_user=False, verbose=True)
        img = Image.open(image_path).convert("RGB")

        # Resize to match the display resolution
        width, height = inky.resolution
        img = img.resize((width, height))

        # Let the Inky library handle quantisation/dithering
        inky.set_image(img)
        inky.show()

        print(f"[DISPLAY] Displayed {image_path}")

    except Exception as ex:
        print(f"[ERROR] Failed to display image: {ex}")

class ImageBrowser:
    def __init__(self, image_dir: Path):
        self.image_dir = image_dir
        self.images = self.scan_images()
        self.index = 0
        self.lock = threading.Lock()

    def scan_images(self):
        if not self.image_dir.exists():
            return []

        files = [
            p for p in self.image_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
        files.sort()
        return files

    def refresh(self):
        with self.lock:
            old_name = None
            if self.images and 0 <= self.index < len(self.images):
                old_name = self.images[self.index].name

            self.images = self.scan_images()

            if not self.images:
                self.index = 0
                return None

            if old_name:
                for i, path in enumerate(self.images):
                    if path.name == old_name:
                        self.index = i
                        break
                else:
                    self.index = min(self.index, len(self.images) - 1)
            else:
                self.index = min(self.index, len(self.images) - 1)

            return self.images[self.index]

    def current(self):
        with self.lock:
            if not self.images:
                return None
            self.index = max(0, min(self.index, len(self.images) - 1))
            return self.images[self.index]

    def next(self):
        with self.lock:
            if not self.images:
                return None
            self.index = (self.index + 1) % len(self.images)
            return self.images[self.index]

    def prev(self):
        with self.lock:
            if not self.images:
                return None
            self.index = (self.index - 1) % len(self.images)
            return self.images[self.index]



class ButtonWatcher(threading.Thread):
    def __init__(self, command_queue: queue.Queue):
        super().__init__(daemon=True)
        self.command_queue = command_queue
        self.stop_event = threading.Event()
        self.last_press_time = 0.0

        input_settings = gpiod.LineSettings(
            direction=Direction.INPUT,
            bias=Bias.PULL_UP,
            edge_detection=Edge.FALLING
        )

        self.chip = gpiodevice.find_chip_by_platform()
        self.offsets = [self.chip.line_offset_from_id(pin) for pin in BUTTONS]
        line_config = dict.fromkeys(self.offsets, input_settings)

        self.request = self.chip.request_lines(
            consumer="inky-image-browser",
            config=line_config
        )

    def run(self):
        print("[BUTTONS] Watching buttons...")

        while not self.stop_event.is_set():
            events = self.request.read_edge_events()
            now = time.monotonic()

            for event in events:
                if now - self.last_press_time < DEBOUNCE_SECONDS:
                    continue

                self.last_press_time = now

                try:
                    idx = self.offsets.index(event.line_offset)
                except ValueError:
                    continue

                label = LABELS[idx]
                print(f"[BUTTONS] Pressed {label}")

                if label == BUTTON_NEXT:
                    self.command_queue.put("next")
                elif label == BUTTON_PREV:
                    self.command_queue.put("prev")


# ------------------------------------------------------------
# Main loop
# ------------------------------------------------------------

running = True
commands = queue.Queue()
watcher = ButtonWatcher(commands)
watcher.start()


def handle_sigint(signum, frame):
    global running
    print("\n[INFO] Stopping...")
    running = False


signal.signal(signal.SIGINT, handle_sigint)
signal.signal(signal.SIGTERM, handle_sigint)


def main():
    print("[INFO] Image stream generator started")

    while running:
        prompt = build_non_repeating_prompt()
        output_file = generate_output_filename()

        ok = run_stable_diffusion(prompt, output_file)

        if ok:
            display_on_inky(output_file)
        else:
            print("[WARN] Skipping display because generation failed")

        # Wait before generating the next one
        for _ in range(DISPLAY_SECONDS):
            if not running:
                break
            time.sleep(1)

    print("[INFO] Exited cleanly")


if __name__ == "__main__":
    main()