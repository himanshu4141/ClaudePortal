"""Host shim for CircuitPython's `board` module.

Pin objects are just opaque sentinels -- the other shims (digitalio, busio,
adafruit_lis3dh) don't actually touch hardware, they only need something to
hold onto. Names mirror the Matrix Portal M4 pinout used by the device code.
"""


class _Pin:
    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:
        return "board.{}".format(self.name)


# ESP32 AirLift co-processor (used by code.py, not by the emulator loop).
ESP_CS = _Pin("ESP_CS")
ESP_BUSY = _Pin("ESP_BUSY")
ESP_RESET = _Pin("ESP_RESET")
SCK = _Pin("SCK")
MOSI = _Pin("MOSI")
MISO = _Pin("MISO")

# I2C (onboard LIS3DH accelerometer).
SCL = _Pin("SCL")
SDA = _Pin("SDA")

# User buttons.
BUTTON_UP = _Pin("BUTTON_UP")
BUTTON_DOWN = _Pin("BUTTON_DOWN")
