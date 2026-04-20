from pathlib import Path

from PIL import Image, ImageOps

from config import HDMI_BACKGROUND, HDMI_FULLSCREEN


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
        self.pygame.event.pump()
