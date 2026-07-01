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

# OnnyxStream

The system uses a version of the Stable Diffusion program which has been optimized to run on very small devices such as the Raspberry Pi Zero 2. It will run on a device with only 512Mb of memory. 

## Installing OnnxStream

This is the installation sequence. Perform these actions from a terminal window on the target machine. 

### Get the tools

We need to the tools to build the program and run the display. 
``` 
sudo apt update
sudo apt install build-essential cmake python3
```

### Make a workspace

We are going to put the OnnyxStream program and the display program in a Programs folder. Let's create the folder and navigate into it:

```
mkdir ~/Programs
cd ~/Programs
```
### Fetch OnnyxStream from GitHub

We get hold of the program source by cloning the GitHub repository containing it.

```
git clone https://github.com/vitoplantamura/OnnxStream
```

### Build the program from source

If you've not built a program from source code you might find this a bit intimidating, but don't worry. The first thing we do is build a *make* file which tells the build system what to do. Then we use that make file to actually create the program code. This complicated sounding process makes it easier to add the flexibility that allows the same C++ program source to run on a huge range of different target hardware. Let's start by moving into the folder containing the source:

```
cd ~/Programs/OnnxStream/src/
```
**Pro tip:** If you press the **tab** key midway through typing the names of the folders in the path there is a good chance that your terminal program will complete the paths for you. Once we have arrived in the src folder we make a **build** folder there and navigate into it. 

```
mkdir build
cd build
```

Now we use the **cmake** program to create the make file. 
```
cmake ..
```
This command is especially confusing. The two dots or periods (..) after the command are very important. They give **cmake** the path to the files that will control what it does. These are held in the **src** folder which is the parent folder to **build**. In the shell the character "." means "the current folder" and the sequence ".." means "the parent folder". So this instruction tells **cmake** that the control files are in the parent folder. 

Now **cmake** has made the build files, the next thing we do is ask it to build the program itself. We add the **--build** option and we tell it to make the **Release** version of the code (i.e. the one without any debugging code)
```
cmake --build . --config Release
```
Note that the single dot (.) is used to tell **cmake** to look in the current folder for all the build control files. On a Raspbery Pi Zero 2 this will take quite a long time to complete. But once it has finished we can ask the newly installed program to tell us about itself:
```
./sd --help
```
There is actually no help command,but this does cause the program to output all its commands.

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
sd --download
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
web_viewer.py           Web interface: gallery browser, prompt editor, SD options
sd_options.py           Schema and defaults for Stable Diffusion command-line options

prompts.json            Runtime prompt overrides (created by the web viewer)
sd_options.json         Runtime SD option overrides (created by the web viewer)
requirements.txt        Python package dependencies
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
* [Stable Diffusion executable (ONNXStream)](#installing-onnxstream)
* **Always required via pip:** `Pillow`, `Flask`
* **HDMI display / keyboard input:** `pygame`
* **Pimoroni e-ink display:** `inky` — installed by the Pimoroni setup script, not via pip
* **Pimoroni button input:** `gpiod`, `gpiodevice` — also installed by the Pimoroni setup script

---

## Installation

### Without a Pimoroni display (HDMI / development)

Create and activate a virtual environment, then install the required packages:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set `DISPLAY_TYPE = "hdmi"` and `INPUT_TYPE = "keyboard"` in `config.py`, then run:

```bash
python3 main.py
```

### With a Pimoroni Inky display

The Pimoroni hardware requires its own installer which sets up a dedicated virtual environment (`~/.virtualenvs/pimoroni`) containing the `inky`, `gpiod`, `gpiodevice`, and `Pillow` libraries. Follow the instructions in the [Pimoroni Inky repository](https://github.com/pimoroni/inky) before proceeding — these libraries cannot be installed reliably via a plain `pip install`.

Once the Pimoroni environment is set up, activate it and install the additional libraries that are not part of the Pimoroni framework:

```bash
source ~/.virtualenvs/pimoroni/bin/activate
pip install Flask
```

`pygame` is not needed in this configuration. Then run:

```bash
python3 main.py
```

#### What the Pimoroni installer provides vs what you add

| Library | Source |
|---|---|
| `inky` | Pimoroni installer |
| `gpiod` | Pimoroni installer |
| `gpiodevice` | Pimoroni installer |
| `Pillow` | Pimoroni installer (as a dependency) |
| `Flask` | You install with `pip install Flask` |
| `pygame` | Not needed for Pimoroni-only setup |

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

Edit `config.py` to point at your SD executable:

```python
SD_COMMAND = "/home/rob/OnnxStream/src/build/sd"
```

All other SD options (model path, steps, memory mode, sampler, etc.) are configured through the **SD Options** tab in the web viewer, or by editing `sd_options.json` directly. See [Web Viewer](#web-viewer) below.

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

`web_viewer.py` provides a browser-based interface. It has three tabs:

* **Gallery** — browse all generated images with their prompts and timestamps, using on-screen buttons or the arrow keys.
* **Prompts** — edit the Stable Diffusion prompt banks, templates, and global quality hint directly from the browser. Changes are saved to `prompts.json` and take effect on the next generated image (no restart needed).
* **SD Options** — enable and configure any Stable Diffusion command-line option (model path, steps, sampler, memory mode, etc.). Changes are saved to `sd_options.json` and take effect on the next generated image (no restart needed).

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

#### Running without a desktop

By default pygame (via SDL2) expects an X11 or Wayland desktop session. On a headless Raspberry Pi OS Lite installation you can drive HDMI output directly through the kernel using the KMS/DRM backend — no desktop required.

Set this environment variable before running:

```bash
SDL_VIDEODRIVER=kmsdrm python3 main.py
```

Or add it to a systemd service unit:

```ini
[Service]
Environment=SDL_VIDEODRIVER=kmsdrm
```

You also need the user running the application to be in the `video`, `render`, and `input` groups (so SDL can access the framebuffer and read keyboard/input events):

```bash
sudo usermod -aG video,render,input rob
```

Log out and back in (or reboot) for group changes to take effect.

> **Note:** A display must be physically connected via HDMI at boot time. This does not work over SSH alone — there is no framebuffer to take over without a screen attached.

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