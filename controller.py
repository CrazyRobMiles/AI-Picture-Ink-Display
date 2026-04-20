import queue
import time

from config import AUTO_DISPLAY_NEW_IMAGES, CATALOG_RESCAN_SECONDS


class Controller:
    def __init__(self, catalog, display_device, command_queue, generated_queue):
        self.catalog = catalog
        self.display_device = display_device
        self.command_queue = command_queue
        self.generated_queue = generated_queue

        self.running = True
        self.auto_mode = AUTO_DISPLAY_NEW_IMAGES
        self.last_catalog_scan = 0.0
        self.latest_generated_image = None
        self.display_busy = False
        self.pending_display = None

    def stop(self):
        self.running = False

    def show(self, image_path):
        if image_path is not None and not self.display_busy:
            self.pending_display = image_path

    def flush_display(self):
        if self.pending_display is None or self.display_busy:
            return

        image_path = self.pending_display
        self.pending_display = None
        self.display_busy = True
        try:
            print(f"[CTRL] Displaying {image_path.name}")
            self.display_device.show_image(image_path)
        finally:
            self.display_busy = False

    def handle_generated_image(self, image_path):
        self.latest_generated_image = image_path
        self.catalog.add_image(image_path)
        print(f"[CTRL] New image: {image_path.name}")

        if self.auto_mode:
            self.show(image_path)
        else:
            print("[CTRL] Auto mode disabled; image saved but not displayed")

    def handle_command(self, cmd: str):
        # Ignore button requests while a display refresh is in progress.
        if self.display_busy and cmd in {"next", "prev", "toggle_auto", "show_latest"}:
            print(f"[CTRL] Ignoring '{cmd}' while display is busy")
            return

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
                if self.latest_generated_image is not None:
                    self.show(self.latest_generated_image)
                else:
                    self.show(self.catalog.latest())

        elif cmd == "show_latest":
            # Jump to the newest image but stay in the current mode.
            if self.latest_generated_image is not None:
                self.show(self.latest_generated_image)
            else:
                self.show(self.catalog.latest())

        elif cmd == "quit":
            self.stop()

    def periodic_refresh(self):
        now = time.monotonic()
        if now - self.last_catalog_scan >= CATALOG_RESCAN_SECONDS:
            self.catalog.refresh()
            self.last_catalog_scan = now

    def _drain_generated_queue(self):
        try:
            while True:
                image_path = self.generated_queue.get_nowait()
                self.handle_generated_image(image_path)
        except queue.Empty:
            pass

    def _drain_command_queue(self):
        try:
            while True:
                cmd = self.command_queue.get_nowait()
                print(f"[CTRL] Command: {cmd}")
                self.handle_command(cmd)
        except queue.Empty:
            pass

    def run(self):
        current = self.catalog.refresh()
        if current is not None:
            if self.auto_mode:
                self.latest_generated_image = self.catalog.latest()
                self.show(self.latest_generated_image)
            else:
                self.show(current)

        while self.running:
            self.periodic_refresh()
            self._drain_generated_queue()
            self._drain_command_queue()
            self.flush_display()

            try:
                self.display_device.process_events()
            except Exception:
                pass

            time.sleep(0.02)
