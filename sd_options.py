"""
Shared schema for the configurable Stable Diffusion command-line options.

Used by config.py (to turn saved settings into the SD_EXTRA_ARGS argv list)
and web_viewer.py (to render and save the "SD Options" editor).
"""

SAMPLER_CHOICES = [
    "euler_a", "euler", "heun", "dpm2", "dpm++2m", "dpm++2mv2", "dpm++2s",
    "dpm++2s_a", "dpm++3msde", "dpm++3msde_a", "ipndm", "ipndm_v", "ipndm_vo",
    "taylor3", "ddpm", "ddpm_a", "ddim", "ddim_a", "tcd", "tcd_a", "lms", "lcm",
]

# kind: "bool" (flag only), "text", "number", or "select" (needs "choices")
OPTION_DEFS = [
    {"flag": "--xl", "kind": "bool", "label": "Stable Diffusion XL 1.0",
     "help": "Runs Stable Diffusion XL 1.0 instead of Stable Diffusion 1.5."},
    {"flag": "--turbo", "kind": "bool", "label": "Stable Diffusion Turbo 1.0",
     "help": "Runs Stable Diffusion Turbo 1.0 instead of Stable Diffusion 1.5."},
    {"flag": "--models-path", "kind": "text", "label": "Models Path",
     "help": "Sets the folder containing the Stable Diffusion models."},
    {"flag": "--ops-printf", "kind": "bool", "label": "Print Operations",
     "help": "During inference, writes the current operation to stdout."},
    {"flag": "--preview-steps", "kind": "bool", "label": "Preview Steps",
     "help": "Save every diffusion step in low resolution."},
    {"flag": "--preview-steps-x8", "kind": "bool", "label": "Preview Steps x8",
     "help": "Magnify previews to full resolution."},
    {"flag": "--decode-steps", "kind": "bool", "label": "Decode Steps",
     "help": "Decode and save every diffusion step in full resolution."},
    {"flag": "--decode-latents", "kind": "text", "label": "Decode Latents File",
     "help": "Skips the diffusion, and decodes the specified latents file."},
    {"flag": "--neg-prompt", "kind": "text", "label": "Negative Prompt",
     "help": "Sets the negative prompt."},
    {"flag": "--num", "kind": "number", "label": "Number of Images",
     "help": "Sets the number of images to generate. Default is 1."},
    {"flag": "--steps", "kind": "number", "label": "Diffusion Steps",
     "help": "Sets the number of diffusion steps. Default is 10."},
    {"flag": "--seed", "kind": "number", "label": "Seed",
     "help": "Sets the seed."},
    {"flag": "--save-latents", "kind": "text", "label": "Save Latents File",
     "help": "After the diffusion, saves the latents in the specified file."},
    {"flag": "--decoder-calibrate", "kind": "bool", "label": "Decoder Calibrate (SD 1.5 only)",
     "help": "Calibrates the quantized version of the VAE decoder."},
    {"flag": "--not-tiled", "kind": "bool", "label": "Not Tiled (SDXL/Turbo only)",
     "help": "Don't use the tiled VAE decoder."},
    {"flag": "--res", "kind": "text", "label": "Resolution (Turbo only)",
     "help": 'Sets the output PNG file resolution. Default is "512x512".'},
    {"flag": "--ram", "kind": "bool", "label": "Load UNET into RAM",
     "help": "Loads the entire UNET model into RAM for faster inference. Sets --not-tiled."},
    {"flag": "--download", "kind": "select", "choices": ["A", "F", "N"], "label": "Download Model",
     "help": "A[uto] / F[orce] / N[ever] (re)download current model."},
    {"flag": "--curl-parallel", "kind": "number", "label": "CURL Parallel Downloads",
     "help": "Sets the number of parallel downloads with CURL. Default is 16."},
    {"flag": "--rpi", "kind": "select", "choices": ["A", "F", "D"], "label": "Raspberry Pi Mode",
     "help": "A[utodetect] / F[orce] / D[isable] to configure the models to run on a Raspberry Pi."},
    {"flag": "--rpi-lowmem", "kind": "bool", "label": "RPi Low Memory",
     "help": "Configures the models to run on a Raspberry Pi Zero 2."},
    {"flag": "--threads", "kind": "number", "label": "Threads",
     "help": "Sets the number of threads, values <= 0 mean max-N."},
    {"flag": "--embed-parameters", "kind": "bool", "label": "Embed Parameters",
     "help": "Store parameters of generation (e.g. model path) in image comments."},
    {"flag": "--sampler", "kind": "select", "choices": SAMPLER_CHOICES, "label": "Sampler",
     "help": "Sampler algorithm. Default is euler_a."},
]

OPTION_FLAGS = {opt["flag"] for opt in OPTION_DEFS}

DEFAULT_SD_OPTIONS = {
    "--rpi-lowmem": {"enabled": True},
    "--steps": {"enabled": True, "value": "40"},
    "--models-path": {"enabled": True, "value": "/home/rob/Models"},
}


def build_args(settings: dict) -> list:
    """Flatten saved {flag: {enabled, value}} settings into an argv list."""
    args = []
    for opt in OPTION_DEFS:
        entry = settings.get(opt["flag"])
        if not entry or not entry.get("enabled"):
            continue
        if opt["kind"] == "bool":
            args.append(opt["flag"])
        else:
            value = str(entry.get("value", "")).strip()
            if value:
                args.append(opt["flag"])
                args.append(value)
    return args
