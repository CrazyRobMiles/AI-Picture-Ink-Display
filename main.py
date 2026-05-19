import queue
import subprocess
import sys
from pathlib import Path

from config import DISPLAY_TYPE, IMAGE_DIR, INPUT_TYPE, WEB_VIEWER_AUTOSTART
from controller import Controller
from display_devices import HdmiDisplayDevice, InkyDisplayDevice
from generator import GeneratorWorker
from image_catalog import ImageCatalog
from input_devices import KeyboardInputWorker, PimoroniButtonInputWorker


def create_display_device():
    if DISPLAY_TYPE == "inky":
        return InkyDisplayDevice()
    if DISPLAY_TYPE == "hdmi":
        return HdmiDisplayDevice()
    raise ValueError(f"Unknown DISPLAY_TYPE: {DISPLAY_TYPE}")


def create_input_worker(command_queue):
    if INPUT_TYPE == "buttons":
        return PimoroniButtonInputWorker(command_queue)
    if INPUT_TYPE == "keyboard":
        return KeyboardInputWorker(command_queue)
    raise ValueError(f"Unknown INPUT_TYPE: {INPUT_TYPE}")


def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    web_proc = None
    if WEB_VIEWER_AUTOSTART:
        web_viewer_path = Path(__file__).parent / "web_viewer.py"
        web_proc = subprocess.Popen([sys.executable, str(web_viewer_path)])
        print(f"[MAIN] Web viewer started (pid {web_proc.pid})")

    command_queue = queue.Queue()
    generated_queue = queue.Queue()

    catalog = ImageCatalog(IMAGE_DIR)
    display_device = create_display_device()
    generator_worker = GeneratorWorker(generated_queue)
    input_worker = create_input_worker(command_queue)

    controller = Controller(
        catalog=catalog,
        display_device=display_device,
        command_queue=command_queue,
        generated_queue=generated_queue,
    )

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
        if web_proc is not None:
            web_proc.terminate()


if __name__ == "__main__":
    main()
