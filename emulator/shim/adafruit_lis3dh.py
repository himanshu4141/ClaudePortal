"""Host shim for the onboard LIS3DH accelerometer.

Reports a flat, face-up board (z ~ +9.8 m/s^2) and never detects a shake, so
the buddy stays in its snapshot-driven states. Shake/face-down behaviour is
exercised on real hardware; set `SIMULATE_*` env vars or poke the instance in
a custom script if you want to drive those paths in the emulator.
"""

import os

_EARTH_G = 9.806


class LIS3DH_I2C:
    def __init__(self, i2c, address=0x19):
        self.i2c = i2c
        self.address = address
        # Allow crude scripted overrides via env for manual testing.
        self._face_down = os.environ.get("EMU_FACE_DOWN") == "1"
        self._shake = os.environ.get("EMU_SHAKE") == "1"

    @property
    def acceleration(self):
        z = -_EARTH_G if self._face_down else _EARTH_G
        return (0.0, 0.0, z)

    def shake(self, shake_threshold=30, avg_count=10, total_delay=0.1):
        return self._shake
