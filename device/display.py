import time

from adafruit_matrixportal.matrix import Matrix

ROTATE_INTERVAL_SECONDS = 5


def make_display(width=64, height=32, bit_depth=4):
    matrix = Matrix(width=width, height=height, bit_depth=bit_depth)
    return matrix.display


class ScreenRotator:
    def __init__(self, display, screens, waiting_screen=None):
        self.display = display
        self.screens = screens
        self.waiting = waiting_screen
        self.snapshot = None
        self.index = 0
        self.last_switch = time.monotonic()
        if waiting_screen is not None:
            self.display.root_group = waiting_screen.group

    def update_snapshot(self, snapshot):
        first_data = self.snapshot is None
        self.snapshot = snapshot
        for screen in self.screens:
            screen.update_data(snapshot)
        if first_data:
            self.last_switch = time.monotonic()
            self.display.root_group = self.screens[self.index].group

    def tick(self):
        if self.snapshot is None:
            return
        if time.monotonic() - self.last_switch >= ROTATE_INTERVAL_SECONDS:
            self.index = (self.index + 1) % len(self.screens)
            self.last_switch = time.monotonic()
            self.display.root_group = self.screens[self.index].group

    def current_index(self):
        return self.index
