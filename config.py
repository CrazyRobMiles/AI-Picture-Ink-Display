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
# Prompts — loaded from prompts.json (edit via the web viewer)
# ------------------------------------------------------------

import json as _json
_PROMPTS_FILE = Path(__file__).parent / "prompts.json"
if _PROMPTS_FILE.exists():
    _p = _json.loads(_PROMPTS_FILE.read_text(encoding="utf-8"))
    PROMPT_BANKS = _p.get("PROMPT_BANKS", {})
    PROMPT_TEMPLATES = _p.get("PROMPT_TEMPLATES", [])
    GLOBAL_QUALITY_HINT = _p.get("GLOBAL_QUALITY_HINT", "")
else:
    PROMPT_BANKS = {}
    PROMPT_TEMPLATES = []
    GLOBAL_QUALITY_HINT = ""

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