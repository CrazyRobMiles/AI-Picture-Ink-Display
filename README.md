# AI-Picture-Ink-Display
Runs on a Pi and displays AI generated pictures on an e-ink panel
# Stable Diffusion E-Ink / Display Frame

A Raspberry Pi–based generative art frame that continuously creates images using Stable Diffusion and displays them on a connected screen.

The system supports:

* Pimoroni Inky Impression e-ink displays
* HDMI monitors (for development or full-colour display)
* Optional local LCD panels
* Hardware button control or keyboard input
* Background image generation with browsing of saved images

---

## OnnyxStream

The system uses a version of the Stable Diffusion program which has been optimized to run on very small devices such as the Raspberry Pi Zero 2. It will run on a device with only 512Mb of memory. Before you can use this system you should install OnnyxStream from here:

https://github.com/vitoplantamura/OnnxStream

### Installation steps

``` 
sudo apt install build-essential cmake python3
git clone https://github.com/vitoplantamura/OnnxStream
cd OnnxStream/src/
mkdir build
cd build
cmake ..
cmake --build . --config Release
./sd --help
```

### Make a shortcut

Edit the bash configuration script:

```
sudo nano ~/.bashrc
```
Add this line at the very end of the file:
```
alias sd='~/Programs/OnnxStream/src/build/sd'
```
Now re-run the configuration script:
```
source ~/.bashrc
```

### Install the model

```
mkdir ~/Models
cd ~/Models
sd download
```

Adding the turbo model:

```
 sd --xl --download
 ```
 
 Adding the turbo XL model (which is really nice)

 ```
  sd --xl --turbo --download
 ```


## Overview

This application combines three core subsystems:

1. **Image Generation**
   Uses a local Stable Diffusion executable (e.g. ONNXStream `sd`) to generate images from dynamically constructed prompts.

2. **Image Display**
   Displays images on a selected output device:

   * E-ink (slow refresh, persistent)
   * HDMI (fast refresh, development-friendly)

3. **User Interaction**
   Allows browsing through previously generated images using:

   * Pimoroni frame buttons
   * Keyboard input (HDMI mode)

The system runs continuously, generating a stream of evolving images while allowing manual exploration.

---

## Features

* Continuous prompt-driven image generation
* Low-memory Stable Diffusion support for Raspberry Pi
* Auto-display mode (new images appear as they are generated)
* Manual browse mode (step through saved images)
* Automatic return to auto mode (optional)
* Threaded architecture for responsiveness
* Pluggable display backends

---

## Project Structure

```text
main.py                 Entry point (full interactive frame)
autoDraw.py             Standalone auto-generate-and-display loop
config.py               Configuration and default prompt definitions

display_devices.py      Display backends (Inky, HDMI)
input_devices.py        Input handlers (buttons, keyboard)
image_catalog.py        Image indexing and navigation
generator.py            Stable Diffusion integration
controller.py           Application state and control logic
web_viewer.py           Web interface: gallery browser and prompt editor

prompts.json            Runtime prompt overrides (created by the web viewer)
```

---

## Requirements

### Hardware

* Raspberry Pi (Pi 4 or Pi 5 recommended)
* Optional:

  * Pimoroni Inky Impression display
  * Pimoroni button frame
  * HDMI monitor (for development or display)

### Software

* Python 3.9+
* Pillow
* Pygame (for HDMI mode)
* Pimoroni Inky library (for e-ink)
* `gpiod` (for button input)
* Stable Diffusion executable (e.g. ONNXStream)

---

## Inky Display Setup

If you are using a Pimoroni Inky display you must install the Pimoroni drivers and set up a virtual environment as described in the [Pimoroni Inky repository](https://github.com/pimoroni/inky). Follow the instructions there before running this application — the Inky library will not be available through a plain `pip install` without the steps described on that page.

Once the virtual environment is set up, activate it before running any of the scripts:

```bash
source ~/.virtualenvs/pimoroni/bin/activate
python3 main.py
```

---

## Stable Diffusion Setup

This application expects a working command-line Stable Diffusion tool. The examples assume that you have stored the code and the sd installation in the path **/home/rob**

Example used:

```bash
/home/rob/OnnxStream/src/build/sd \
  --prompt "a mechanical owl" \
  --models-path /home/rob/Models" \
  --rpi-lowmem \
  --passes 6
```

### Configuration

Edit `config.py`:

```python
SD_COMMAND = "/home/rob/OnnxStream/src/build/sd"

SD_EXTRA_ARGS = [
    "--rpi-lowmem",
    "--passes", "6",
    "--models-path", "/home/rob/Models"
]
```

Adjust arguments to match your working setup.

---

## Running the Application

```bash
python3 main.py
```

For the simpler standalone auto-draw loop (no interactive browsing):

```bash
python3 autoDraw.py
```

---

## Web Viewer

`web_viewer.py` provides a browser-based interface. It has two tabs:

* **Gallery** — browse all generated images with their prompts and timestamps, using on-screen buttons or the arrow keys.
* **Prompts** — edit the Stable Diffusion prompt banks, templates, and global quality hint directly from the browser. Changes are saved to `prompts.json` and take effect on the next generated image (no restart needed).

### Configuration

Set in `config.py`:

```python
WEB_VIEWER_AUTOSTART = False   # Launch web viewer automatically alongside main.py
WEB_VIEWER_HOST = "0.0.0.0"   # Interface to bind (0.0.0.0 = all interfaces)
WEB_VIEWER_PORT = 8080         # Port (channel) the web viewer listens on
```

### Running manually

```bash
python3 web_viewer.py
```

Then open `http://<pi-address>:8080/` in a browser (replace `8080` if you changed `WEB_VIEWER_PORT`).

The web viewer can run alongside `main.py` or `autoDraw.py`; it only reads and writes files and does not interact with the display hardware.

### Autostart alongside main.py

Set `WEB_VIEWER_AUTOSTART = True` in `config.py` to have `main.py` launch the web viewer automatically as a separate process on startup. It will be stopped cleanly when `main.py` exits.

This is the simplest option when you want both running together without managing two services.

### How prompt editing works

The web viewer saves edits to `prompts.json` in the project directory. On every iteration, `autoDraw.py` reloads `config.py`, which automatically picks up `prompts.json` if it exists. The original defaults in `config.py` are used as the fallback when no override file is present.

### Autostart on boot (systemd)

Create the service file:

```bash
sudo nano /etc/systemd/system/ai-web-viewer.service
```

Paste the following (adjust `User` and paths if your setup differs):

```ini
[Unit]
Description=AI Picture Frame Web Viewer
After=network.target

[Service]
Type=simple
User=rob
WorkingDirectory=/home/rob/AI-Picture-Ink-Display
ExecStart=/usr/bin/python3 /home/rob/AI-Picture-Ink-Display/web_viewer.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-web-viewer
sudo systemctl start ai-web-viewer
```

Check that it is running:

```bash
sudo systemctl status ai-web-viewer
```

View logs:

```bash
journalctl -u ai-web-viewer -f
```

The same pattern works for `autoDraw.py` — create a second service file (e.g. `ai-autodraw.service`) pointing to `autoDraw.py`.

---

## Display Modes

Set in `config.py`:

```python
DISPLAY_TYPE = "inky"   # or "hdmi"
```

### Inky (E-ink)

* Optimised for low refresh rate
* Persistent image display
* Uses Pimoroni Inky library

### HDMI

* Fullscreen display using Pygame
* Ideal for development and testing
* Fast refresh and keyboard control

---

## Input Modes

Set in `config.py`:

```python
INPUT_TYPE = "buttons"   # or "keyboard"
```

### Pimoroni Buttons

Default mapping for the buttons on the [Pimoroni Inky Impression 7.3 inch display](https://shop.pimoroni.com/products/inky-impression)

| Button | Action            |
| ------ | ----------------- |
| A      | Next image        |
| B      | Previous image    |
| C      | Toggle auto mode  |
| D      | Show latest image |

### Keyboard (HDMI mode)

| Key     | Action            |
| ------- | ----------------- |
| →       | Next image        |
| ←       | Previous image    |
| Space   | Toggle auto mode  |
| Home    | Show latest image |
| Esc / Q | Quit              |

---

## Operating Modes

### Auto Mode

* Newly generated images are displayed automatically
* The system behaves like a live generative picture frame

### Manual Browse Mode

* Entered when pressing Next/Previous
* Allows navigation through stored images
* Generation continues in the background

### Returning to Auto Mode

* Press the toggle button (C or Space)
---

## Image Storage

Generated images are stored in:

```text
/home/rob/generated_images
```

Each file is timestamped:

```text
image_YYYYMMDD_HHMMSS.png
```

A log file records prompts:

```text
prompt_log.txt
```

---

## Prompt Generation

Prompts are constructed from word banks:

* subjects
* styles
* moods
* details
* environment

Example:

```text
a mechanical owl, engraving, mysterious, high contrast,above the clouds
```

These can be customised in `config.py`.

---

## Architecture Notes

* **Generator thread** runs Stable Diffusion in the background

* **Input thread** handles buttons or keyboard

* **Display system**:

  * Main-thread driven for HDMI (required for SDL/EGL) and e-ink

* **Controller** manages:

  * current image index
  * auto vs manual mode
  * display requests

---

## Troubleshooting

### Stable Diffusion fails with code 137

* Out of memory
* Use:

  ```bash
  --rpi lowmem
  --passes 6
  ```
* Reduce workload further if needed

---

### Images not appearing

* Check `auto_mode` is enabled
* Confirm images exist in output directory
* Verify display backend is correct

---

### HDMI error: EGL_BAD_ACCESS

* Ensure display runs in main thread
* Do not call Pygame display functions from worker threads

---

### Buttons not responding

* Verify GPIO mapping using:

  ```bash
  gpioinfo
  ```
* Check `BUTTON_PINS` in `config.py`

---

## Future Enhancements

* On-screen overlays (prompt, mode, filename)
* Favourites and deletion controls
* Network control interface
* Multiple prompt themes
* Scheduled generation profiles

---

## Summary

This project turns a Raspberry Pi into a self-contained generative art system:

* continuously creates images
* displays them on e-ink or HDMI
* allows interactive browsing
* runs unattended as a digital picture frame

It is designed to be modular, extensible, and adaptable to different display hardware.

---

Have fun!

Rob Miles : [robmiles.com](https://robmiles.com)