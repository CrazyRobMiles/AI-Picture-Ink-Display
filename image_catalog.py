import threading
from pathlib import Path


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


class ImageCatalog:
    def __init__(self, image_dir: Path):
        self.image_dir = image_dir
        self.lock = threading.Lock()
        self.images = []
        self.index = -1

    def scan_images(self):
        files = [
            p for p in self.image_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
        files.sort()
        return files

    def refresh(self):
        with self.lock:
            old_current = self.current()

            if not self.image_dir.exists():
                self.images = []
                self.index = -1
                return None

            self.images = self.scan_images()

            if not self.images:
                self.index = -1
                return None

            if old_current and old_current in self.images:
                self.index = self.images.index(old_current)
            elif self.index < 0:
                self.index = 0
            else:
                self.index = min(self.index, len(self.images) - 1)

            return self.current()

    def add_image(self, image_path: Path):
        with self.lock:
            if image_path not in self.images:
                self.images.append(image_path)
                self.images.sort()

    def count(self):
        with self.lock:
            return len(self.images)

    def current(self):
        if not self.images:
            return None
        if self.index < 0:
            return None
        self.index = max(0, min(self.index, len(self.images) - 1))
        return self.images[self.index]

    def latest(self):
        with self.lock:
            if not self.images:
                return None
            self.index = len(self.images) - 1
            return self.images[self.index]

    def next(self):
        with self.lock:
            if not self.images:
                return None
            self.index = (self.index + 1) % len(self.images)
            return self.images[self.index]

    def prev(self):
        with self.lock:
            if not self.images:
                return None
            self.index = (self.index - 1) % len(self.images)
            return self.images[self.index]