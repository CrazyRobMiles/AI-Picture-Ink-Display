from pathlib import Path

# ------------------------------------------------------------
# General settings
# ------------------------------------------------------------

IMAGE_DIR = Path("/home/rob/generated_images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

DISPLAY_TYPE = "inky"          # "inky" or "hdmi"
INPUT_TYPE = "buttons"         # "buttons" or "keyboard"
DISPLAY_FIT_MODE = "stretch"   # "contain", "crop", or "stretch"

AUTO_DISPLAY_NEW_IMAGES = True
DISPLAY_QUEUE_POLL_SECONDS = 0.1
CATALOG_RESCAN_SECONDS = 5.0
FAIL_RETRY_SECONDS = 60
MAX_RECENT_PROMPTS = 12

# ------------------------------------------------------------
# Stable Diffusion settings
# ------------------------------------------------------------

# Stable Diffusion executable
SD_COMMAND = "/home/rob/OnnxStream/src/build/sd"

# Extra arguments for your working setup
SD_EXTRA_ARGS = [
    "--rpi-lowmem",
    "--steps", "10",
    "--models-path", "/home/rob/Models" 
]

# If your generator uses different argument names, change these.
SD_PROMPT_ARG = "--prompt"
SD_OUTPUT_ARG = "--output"

# ------------------------------------------------------------
# Prompt banks
# ------------------------------------------------------------

SUBJECTS = [
    "a lonely lighthouse",
    "a Victorian greenhouse",
    "a steam train crossing a viaduct",
    "an ancient oak tree",
    "a moonlit city street",
    "a retro-futuristic robot",
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
]

STYLES = [
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
]

MOODS = [
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
]

DETAILS = [
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
]

ENVIRONMENT = [
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

# ------------------------------------------------------------
# Pimoroni button settings
# ------------------------------------------------------------

# Pimoroni example mapping for some Raspberry Pi platforms.
# If needed, confirm with gpioinfo.
BUTTON_PINS = [5, 6, 16, 24]   # A, B, C, D
BUTTON_LABELS = ["A", "B", "C", "D"]

BUTTON_NEXT = "A"
BUTTON_PREV = "B"
BUTTON_TOGGLE_AUTO = "C"
BUTTON_SHOW_LATEST = "D"

BUTTON_DEBOUNCE_SECONDS = 0.25

# ------------------------------------------------------------
# HDMI settings
# ------------------------------------------------------------

HDMI_FULLSCREEN = True
HDMI_BACKGROUND = (0, 0, 0)