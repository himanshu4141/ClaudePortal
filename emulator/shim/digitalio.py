"""Host shim for CircuitPython's `digitalio` module.

Buttons read as "not pressed" (value True, since the device uses active-low
pull-ups). Pet selection via buttons therefore stays put in the emulator;
use keyboard/CLI controls instead if interactive pet-switching is needed.
"""


class Pull:
    UP = "UP"
    DOWN = "DOWN"


class Direction:
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"


class DigitalInOut:
    def __init__(self, pin):
        self.pin = pin
        self.direction = Direction.INPUT
        self.pull = None
        self._value = True  # active-low buttons idle high (unpressed)

    def switch_to_input(self, pull=None):
        self.direction = Direction.INPUT
        self.pull = pull

    def switch_to_output(self, value=False):
        self.direction = Direction.OUTPUT
        self._value = value

    def deinit(self):
        pass

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v
