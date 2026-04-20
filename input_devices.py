import queue
import threading
import time

from config import (
    BUTTON_DEBOUNCE_SECONDS,
    BUTTON_LABELS,
    BUTTON_NEXT,
    BUTTON_PINS,
    BUTTON_PREV,
    BUTTON_SHOW_LATEST,
    BUTTON_TOGGLE_AUTO,
)


class InputWorker(threading.Thread):
    def __init__(self, command_queue: queue.Queue):
        super().__init__(daemon=True)
        self.command_queue = command_queue
        self.running = True

    def stop(self):
        self.running = False


class PimoroniButtonInputWorker(InputWorker):
    def __init__(self, command_queue: queue.Queue):
        super().__init__(command_queue)

        import gpiod
        import gpiodevice
        from gpiod.line import Bias, Direction, Edge

        self.gpiod = gpiod
        self.last_press_time = 0.0

        input_settings = gpiod.LineSettings(
            direction=Direction.INPUT,
            bias=Bias.PULL_UP,
            edge_detection=Edge.FALLING
        )

        self.chip = gpiodevice.find_chip_by_platform()
        self.offsets = [self.chip.line_offset_from_id(pin) for pin in BUTTON_PINS]
        line_config = dict.fromkeys(self.offsets, input_settings)

        self.request = self.chip.request_lines(
            consumer="sd-frame-buttons",
            config=line_config
        )

    def map_label_to_command(self, label: str):
        if label == BUTTON_NEXT:
            return "next"
        if label == BUTTON_PREV:
            return "prev"
        if label == BUTTON_TOGGLE_AUTO:
            return "toggle_auto"
        if label == BUTTON_SHOW_LATEST:
            return "show_latest"
        return None

    def run(self):
        print("[INPUT] Button input active")
        while self.running:
            events = self.request.read_edge_events()
            now = time.monotonic()

            for event in events:
                if now - self.last_press_time < BUTTON_DEBOUNCE_SECONDS:
                    continue

                self.last_press_time = now

                try:
                    idx = self.offsets.index(event.line_offset)
                except ValueError:
                    continue

                label = BUTTON_LABELS[idx]
                command = self.map_label_to_command(label)

                if command:
                    print(f"[INPUT] Button {label} -> {command}")
                    self.command_queue.put(command)


class KeyboardInputWorker(InputWorker):
    """
    HDMI-friendly keyboard control.

    Right arrow : next
    Left arrow  : prev
    Space       : toggle_auto
    Home        : show_latest
    Esc / q     : quit
    """
    def __init__(self, command_queue: queue.Queue):
        super().__init__(command_queue)
        import pygame
        self.pygame = pygame

    def run(self):
        print("[INPUT] Keyboard input active")
        while self.running:
            for event in self.pygame.event.get():
                if event.type == self.pygame.QUIT:
                    self.command_queue.put("quit")
                elif event.type == self.pygame.KEYDOWN:
                    if event.key == self.pygame.K_RIGHT:
                        self.command_queue.put("next")
                    elif event.key == self.pygame.K_LEFT:
                        self.command_queue.put("prev")
                    elif event.key == self.pygame.K_SPACE:
                        self.command_queue.put("toggle_auto")
                    elif event.key == self.pygame.K_HOME:
                        self.command_queue.put("show_latest")
                    elif event.key in (self.pygame.K_ESCAPE, self.pygame.K_q):
                        self.command_queue.put("quit")

            time.sleep(0.05)