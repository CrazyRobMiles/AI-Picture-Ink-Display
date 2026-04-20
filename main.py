import queue

from config import DISPLAY_TYPE, IMAGE_DIR, INPUT_TYPE
from controller import Controller
from display_devices import DisplayWorker, HdmiDisplayDevice, InkyDisplayDevice
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

    command_queue = queue.Queue()
    generated_queue = queue.Queue()

    catalog = ImageCatalog(IMAGE_DIR)
    display_device = create_display_device()
    display_worker = DisplayWorker(display_device)
    generator_worker = GeneratorWorker(generated_queue)
    input_worker = create_input_worker(command_queue)

    controller = Controller(
        catalog=catalog,
        display_worker=display_worker,
        command_queue=command_queue,
        generated_queue=generated_queue,
    )

    display_worker.start()
    generator_worker.start()
    input_worker.start()

    try:
        controller.run()
    except KeyboardInterrupt:
        print("\n[MAIN] Stopping...")
    finally:
        controller.stop()
        display_worker.stop()
        generator_worker.stop()
        input_worker.stop()


if __name__ == "__main__":
    main()