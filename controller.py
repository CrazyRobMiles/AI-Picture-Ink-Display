import queue
import threading
import time

from config import AUTO_DISPLAY_NEW_IMAGES, CATALOG_RESCAN_SECONDS


class Controller:
    def __init__(self, catalog, display_worker, command_queue, generated_queue):
        self.catalog = catalog
        self.display_worker = display_worker
        self.command_queue = command_queue
        self.generated_queue = generated_queue

        self.running = True
        self.auto_mode = AUTO_DISPLAY_NEW_IMAGES
        self.last_catalog_scan = 0.0

    def stop(self):
        self.running = False

    def show(self, image_path):
        if image_path is not None:
            self.display_worker.request_display(image_path)

    def handle_generated_image(self, image_path):
        self.catalog.add_image(image_path)
        print(f"[CTRL] New image: {image_path.name}")

        if self.auto_mode:
            latest = self.catalog.latest()
            self.show(latest)

    def handle_command(self, cmd: str):
        if cmd == "next":
            self.auto_mode = False
            self.show(self.catalog.next())

        elif cmd == "prev":
            self.auto_mode = False
            self.show(self.catalog.prev())

        elif cmd == "toggle_auto":
            self.auto_mode = not self.auto_mode
            print(f"[CTRL] auto_mode = {self.auto_mode}")
            if self.auto_mode:
                self.show(self.catalog.latest())

        elif cmd == "show_latest":
            self.auto_mode = False
            self.show(self.catalog.latest())

        elif cmd == "quit":
            self.stop()

    def periodic_refresh(self):
        now = time.monotonic()
        if now - self.last_catalog_scan >= CATALOG_RESCAN_SECONDS:
            self.catalog.refresh()
            self.last_catalog_scan = now

    def run(self):
        current = self.catalog.refresh()
        if current is not None:
            if self.auto_mode:
                self.show(self.catalog.latest())
            else:
                self.show(current)

        while self.running:
            self.periodic_refresh()

            try:
                while True:
                    image_path = self.generated_queue.get_nowait()
                    self.handle_generated_image(image_path)
            except queue.Empty:
                pass

            try:
                cmd = self.command_queue.get(timeout=0.2)
                print(f"[CTRL] Command: {cmd}")
                self.handle_command(cmd)
            except queue.Empty:
                pass