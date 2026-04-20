from pathlib import Path

# ------------------------------------------------------------
# General settings
# ------------------------------------------------------------

IMAGE_DIR = Path("/home/rob/generated_images")
IMAGE_DIR.mkdir(parents=True, exist_ok=True)

DISPLAY_TYPE = "inky"          # "inky" or "hdmi"
INPUT_TYPE = "buttons"         # "buttons" or "keyboard"

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
    "--steps", "6",
    "--models-path", "/home/rob/Models" 
]

# If your generator uses different argument names, change these.
SD_PROMPT_ARG = "--prompt"
SD_OUTPUT_ARG = "--output"

# ------------------------------------------------------------
# Prompt banks
# ------------------------------------------------------------

SUBJECTS = [
    "a lonely lighthouse on a cliff",
    "a steam train crossing a viaduct",
    "a Victorian observatory",
    "a mechanical owl",
    "an ancient oak tree",
    "a moonlit ruined abbey",
    "a floating island above clouds",
    "a forest path in mist",
    "a glass greenhouse full of exotic plants",
    "a quiet harbour at dusk",
]

STYLES = [
    "oil painting",
    "engraving",
    "storybook illustration",
    "woodcut print",
    "cinematic concept art",
    "dreamlike surrealism",
    "ink drawing",
    "retro poster art",
]

MOODS = [
    "mysterious",
    "peaceful",
    "haunting",
    "nostalgic",
    "uplifting",
    "otherworldly",
]

DETAILS = [
    "high contrast",
    "dramatic lighting",
    "bold shapes",
    "strong composition",
    "intricate detail",
    "atmospheric depth",
    "rich textures",
    "simple composition",
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