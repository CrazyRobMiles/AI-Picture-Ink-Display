import threading
import time
from pathlib import Path

from PIL import Image, ImageOps

from config import (
    DISPLAY_QUEUE_POLL_SECONDS,
    HDMI_BACKGROUND,
    HDMI_FULLSCREEN,
)


def fit_image(img, target_width, target_height, background=(255, 255, 255)):
    img = img.convert("RGB")
    fitted = ImageOps.contain(img, (target_width, target_height))
    canvas = Image.new("RGB", (target_width, target_height), background)
    x = (target_width - fitted.width) // 2
    y = (target_height - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return canvas


class DisplayDevice:
    def get_size(self):
        raise NotImplementedError

    def show_image(self, image_path: Path):
        raise NotImplementedError

    def process_events(self):
        """Optional hook for windowed backends."""
        pass


class InkyDisplayDevice(DisplayDevice):
    def __init__(self):
        from inky.auto import auto

        self.inky = auto(ask_user=False, verbose=True)
        self.width, self.height = self.inky.resolution

    def get_size(self):
        return self.width, self.height

    def show_image(self, image_path: Path):
        img = Image.open(image_path)
        img = fit_image(img, self.width, self.height, background=(255, 255, 255))
        self.inky.set_image(img)
        self.inky.show()


class HdmiDisplayDevice(DisplayDevice):
    def __init__(self):
        import pygame

        pygame.init()
        self.pygame = pygame

        info = pygame.display.Info()
        self.width = info.current_w
        self.height = info.current_h

        flags = pygame.FULLSCREEN if HDMI_FULLSCREEN else 0
        self.screen = pygame.display.set_mode((self.width, self.height), flags)
        pygame.display.set_caption("Stable Diffusion Frame")
        self.background = HDMI_BACKGROUND

    def get_size(self):
        return self.width, self.height

    def show_image(self, image_path: Path):
        img = Image.open(image_path)
        img = fit_image(img, self.width, self.height, background=self.background)

        mode = img.mode
        size = img.size
        data = img.tobytes()

        surface = self.pygame.image.fromstring(data, size, mode)
        self.screen.blit(surface, (0, 0))
        self.pygame.display.flip()

    def process_events(self):
        # Prevent the window manager from thinking the app is hung.
        self.pygame.event.pump()


class DisplayWorker(threading.Thread):
    """
    Latest-image display worker.
    Only this thread talks to the display hardware.
    """
    def __init__(self, display_device: DisplayDevice):
        super().__init__(daemon=True)
        self.display_device = display_device
        self.running = True
        self.lock = threading.Lock()
        self.pending_image = None
        self.last_image = None

    def request_display(self, image_path: Path):
        with self.lock:
            self.pending_image = image_path

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            image_path = None

            with self.lock:
                if self.pending_image is not None:
                    image_path = self.pending_image
                    self.pending_image = None

            if image_path is not None and image_path != self.last_image:
                try:
                    print(f"[DISPLAY] Showing {image_path.name}")
                    self.display_device.show_image(image_path)
                    self.last_image = image_path
                except Exception as ex:
                    print(f"[DISPLAY ERROR] {ex}")
            else:
                try:
                    self.display_device.process_events()
                except Exception:
                    pass
                time.sleep(DISPLAY_QUEUE_POLL_SECONDS)