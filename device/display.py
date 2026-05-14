import time

from adafruit_matrixportal.matrix import Matrix

ROTATE_INTERVAL_SECONDS = 5


def make_display(width=64, height=32, bit_depth=4):
    matrix = Matrix(width=width, height=height, bit_depth=bit_depth)
    return matrix.display


class ScreenRotator:
    def __init__(self, display, screen_factories, waiting_factory=None):
        self.display = display
        self.factories = screen_factories
        self.waiting_factory = waiting_factory
        self.snapshot = None
        self.index = 0
        self.last_switch = time.monotonic()
        if waiting_factory is not None:
            self.display.root_group = waiting_factory()

    def update_snapshot(self, snapshot):
        first_data = self.snapshot is None
        self.snapshot = snapshot
        if first_data:
            self.last_switch = time.monotonic()
        self._render()

    def tick(self):
        if self.snapshot is None:
            return
        if time.monotonic() - self.last_switch >= ROTATE_INTERVAL_SECONDS:
            self.index = (self.index + 1) % len(self.factories)
            self.last_switch = time.monotonic()
            self._render()

    def _render(self):
        if self.snapshot is None:
            return
        group = self.factories[self.index](self.snapshot)
        self.display.root_group = group
