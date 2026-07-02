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
SD_COMMAND = "/home/rob/Programs/OnnxStream/src/build/sd"

# If your generator uses different argument names, change these.
SD_PROMPT_ARG = "--prompt"
SD_OUTPUT_ARG = "--output"

# ------------------------------------------------------------
# Prompt banks
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

# If enabled, this text is appended to every prompt
GLOBAL_QUALITY_HINT = "high detail, beautiful composition"

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

# ------------------------------------------------------------
# Web viewer settings
# ------------------------------------------------------------

WEB_VIEWER_AUTOSTART = True   # Launch web viewer automatically as a separate process
WEB_VIEWER_HOST = "0.0.0.0"
WEB_VIEWER_PORT = 8080         # Port (channel) the web viewer listens on

# ------------------------------------------------------------
# Runtime prompt overrides (written by the web viewer)
# ------------------------------------------------------------

import json as _json
_PROMPTS_OVERRIDE = Path(__file__).parent / "prompts.json"
if _PROMPTS_OVERRIDE.exists():
    with _PROMPTS_OVERRIDE.open("r", encoding="utf-8") as _f:
        _data = _json.load(_f)
    PROMPT_BANKS = _data.get("PROMPT_BANKS", PROMPT_BANKS)
    PROMPT_TEMPLATES = _data.get("PROMPT_TEMPLATES", PROMPT_TEMPLATES)
    GLOBAL_QUALITY_HINT = _data.get("GLOBAL_QUALITY_HINT", GLOBAL_QUALITY_HINT)

# ------------------------------------------------------------
# Runtime SD option overrides (written by the web viewer)
# ------------------------------------------------------------

_APP_SETTINGS_FILE = Path(__file__).parent / "app_settings.json"
if _APP_SETTINGS_FILE.exists():
    with _APP_SETTINGS_FILE.open("r", encoding="utf-8") as _f:
        _app = _json.load(_f)
    DISPLAY_TYPE = _app.get("DISPLAY_TYPE", DISPLAY_TYPE)
    INPUT_TYPE = _app.get("INPUT_TYPE", INPUT_TYPE)

from sd_options import DEFAULT_SD_OPTIONS, build_args

_SD_OPTIONS_FILE = Path(__file__).parent / "sd_options.json"
if _SD_OPTIONS_FILE.exists():
    with _SD_OPTIONS_FILE.open("r", encoding="utf-8") as _f:
        SD_OPTIONS = _json.load(_f)
else:
    SD_OPTIONS = DEFAULT_SD_OPTIONS

SD_EXTRA_ARGS = build_args(SD_OPTIONS)