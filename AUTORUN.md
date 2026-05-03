autorun.md

# Running the AI Picture Ink Display on Boot

This guide explains how to configure the application to automatically start when the Raspberry Pi powers on using a systemd service.

---

## Overview

The application is started using:

```
/home/rob/.virtualenvs/pimoroni/bin/python /home/rob/code/AI-Picture-Ink-Display/main.py
```

This guide configures Linux to run that command automatically at boot.

---

## Why systemd?

systemd is the recommended approach because it:

* Starts the application automatically at boot
* Restarts it if it crashes
* Provides logging and status monitoring
* Runs without requiring a user to log in

---

## Step 1 — Create the service file

Create a new service definition:

```
sudo nano /etc/systemd/system/ai-picture-ink-display.service
```

Add the following content:

```
[Unit]
Description=AI Picture Ink Display
After=network.target

[Service]
Type=simple
User=rob
WorkingDirectory=/home/rob/code/AI-Picture-Ink-Display

ExecStart=/home/rob/.virtualenvs/pimoroni/bin/python /home/rob/code/AI-Picture-Ink-Display/main.py

Restart=always
RestartSec=5

Environment=PYTHONUNBUFFERED=1

# Required if using HDMI / pygame display mode
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/rob/.Xauthority

# Optional: delay startup to allow hardware to initialise
ExecStartPre=/bin/sleep 10

[Install]
WantedBy=multi-user.target
```

---

## Step 2 — Enable the service

Reload systemd and enable the service:

```
sudo systemctl daemon-reload
sudo systemctl enable ai-picture-ink-display.service
```

---

## Step 3 — Start the service

Start it manually for testing:

```
sudo systemctl start ai-picture-ink-display.service
```

---

## Step 4 — Check status and logs

Check if the service is running:

```
systemctl status ai-picture-ink-display.service
```

View live logs:

```
journalctl -u ai-picture-ink-display.service -f
```

---

## Step 5 — Test on reboot

Reboot the Raspberry Pi:

```
sudo reboot
```

After boot, the application should start automatically.

---

## Managing the service

### Stop the application

```
sudo systemctl stop ai-picture-ink-display.service
```

### Restart the application

```
sudo systemctl restart ai-picture-ink-display.service
```

### Disable auto-start

```
sudo systemctl disable ai-picture-ink-display.service
```

---

## Notes on Python environments

This project uses a virtual environment located at:

```
~/.virtualenvs/pimoroni
```

Important:

* Do NOT use "source .../activate" in the service
* Always call the virtualenv Python directly in ExecStart

---

## Hardware considerations

### Inky Display

* Works headless
* No additional configuration required

### HDMI / pygame display

Requires:

```
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/rob/.Xauthority
```

---

## Troubleshooting

### Service does not start

Check logs:

```
journalctl -u ai-picture-ink-display.service
```

---

### Display not working

Ensure the desktop environment is running.

Test manually:

```
DISPLAY=:0 python main.py
```

---

### Buttons not working

Ensure the user is in the gpio group:

```
sudo usermod -aG gpio rob
```

Then reboot.

---

### Program starts too early

Add a startup delay:

```
ExecStartPre=/bin/sleep 10
```

---

## Summary

After completing this setup:

* The application starts automatically at boot
* It runs using the correct Python virtual environment
* It restarts automatically if it crashes
* It can be controlled using standard systemd commands
