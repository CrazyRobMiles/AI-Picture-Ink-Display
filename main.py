import queue
import threading

import config
from display_devices import HdmiDisplayDevice, InkyDisplayDevice, NullDisplayDevice
from generator import GeneratorWorker
from image_catalog import ImageCatalog
from input_devices import KeyboardInputWorker, NullInputWorker, PimoroniButtonInputWorker
from controller import Controller


def create_display_device():
    display_type = config.DISPLAY_TYPE
    try:
        if display_type == "inky":
            return InkyDisplayDevice()
        if display_type == "hdmi":
            return HdmiDisplayDevice()
        raise ValueError(f"Unknown DISPLAY_TYPE: {display_type!r}")
    except Exception as e:
        print(f"[MAIN] Display device unavailable ({e}) — running without display")
        return NullDisplayDevice()


def create_input_worker(command_queue):
    input_type = config.INPUT_TYPE
    try:
        if input_type == "buttons":
            return PimoroniButtonInputWorker(command_queue)
        if input_type == "keyboard":
            return KeyboardInputWorker(command_queue)
        raise ValueError(f"Unknown INPUT_TYPE: {input_type!r}")
    except Exception as e:
        print(f"[MAIN] Input device unavailable ({e}) — running without input")
        return NullInputWorker(command_queue)


def main() -> bool:
    """Run one application lifecycle. Returns True if a restart was requested."""
    config.IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    restart_event = threading.Event()
    web_server = None

    if config.WEB_VIEWER_AUTOSTART:
        from web_viewer import WebViewerThread, set_restart_event
        set_restart_event(restart_event)
        web_server = WebViewerThread()
        web_server.start()

    command_queue = queue.Queue()
    generated_queue = queue.Queue()

    catalog = ImageCatalog(config.IMAGE_DIR)
    display_device = create_display_device()
    generator_worker = GeneratorWorker(generated_queue)
    input_worker = create_input_worker(command_queue)

    controller = Controller(
        catalog=catalog,
        display_device=display_device,
        command_queue=command_queue,
        generated_queue=generated_queue,
    )

    # When the restart event fires, push a quit command so the controller exits cleanly.
    def _restart_watcher():
        restart_event.wait()
        command_queue.put("quit")
    threading.Thread(target=_restart_watcher, daemon=True).start()

    generator_worker.start()
    input_worker.start()

    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping...")
    finally:
        controller.stop()
        generator_worker.stop()
        input_worker.stop()
        if web_server is not None:
            set_restart_event(None)
            web_server.stop()

    return restart_event.is_set()


if __name__ == "__main__":
    while main():
        print("[MAIN] Restarting with new settings...")
