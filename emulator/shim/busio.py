"""Host shim for CircuitPython's `busio` module.

I2C/SPI are no-op handles. The LIS3DH shim ignores the bus entirely, so these
just need to construct without touching hardware.
"""


class I2C:
    def __init__(self, scl=None, sda=None, frequency=400000):
        self.scl = scl
        self.sda = sda
        self.frequency = frequency

    def deinit(self):
        pass


class SPI:
    def __init__(self, clock=None, MOSI=None, MISO=None):
        self.clock = clock
        self.mosi = MOSI
        self.miso = MISO

    def deinit(self):
        pass
