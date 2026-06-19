"""Physical inputs for the Matrix Portal M4: onboard LIS3DH + UP/DOWN buttons.

- shake  -> dizzy (LIS3DH .shake())
- face-down -> nap (LIS3DH z axis; flat face-up reads z ~ +9.8, face-down ~ -9.8)
- UP/DOWN buttons -> cycle the selected pet (the ONLY thing buttons do)

The chosen pet index persists in microcontroller.nvm[0] across reboots. Everything
degrades gracefully: a missing accelerometer or nvm just disables that feature
rather than crashing the panel.
"""

import board
import digitalio

import pets

_FACE_DOWN_Z = -5.0      # m/s^2; below this the board is face-down
_SHAKE_THRESHOLD = 15    # LIS3DH .shake() sensitivity (higher = harder shake)
_NVM_PET_SLOT = 0


def _make_lis3dh():
    try:
        import busio
        import adafruit_lis3dh
        i2c = busio.I2C(board.SCL, board.SDA)
        return adafruit_lis3dh.LIS3DH_I2C(i2c, address=0x19)
    except Exception as exc:  # noqa: BLE001 - sensor optional; keep panel alive
        print("inputs: LIS3DH unavailable ({})".format(exc))
        return None


def _make_button(pin):
    btn = digitalio.DigitalInOut(pin)
    btn.switch_to_input(pull=digitalio.Pull.UP)
    return btn


class PetSelector:
    """Current pet index, persisted to nvm. UP/DOWN nudge it within the registry."""

    def __init__(self):
        self._nvm = getattr(__import__("microcontroller"), "nvm", None)
        self.index = self._load()

    def _load(self):
        if self._nvm is None:
            return 0
        try:
            return self._nvm[_NVM_PET_SLOT] % pets.count()
        except Exception:  # noqa: BLE001
            return 0

    def _save(self):
        if self._nvm is None:
            return
        try:
            self._nvm[_NVM_PET_SLOT] = self.index
        except Exception:  # noqa: BLE001
            pass

    def nudge(self, delta):
        if not delta:
            return self.index
        self.index = (self.index + delta) % pets.count()
        self._save()
        return self.index

    def name(self):
        return pets.name_at(self.index)

    def load_module(self):
        return pets.load(self.index)


class Inputs:
    def __init__(self):
        self._lis = _make_lis3dh()
        try:
            self._up = _make_button(board.BUTTON_UP)
            self._down = _make_button(board.BUTTON_DOWN)
        except Exception as exc:  # noqa: BLE001
            print("inputs: buttons unavailable ({})".format(exc))
            self._up = self._down = None
        self._up_was = False
        self._down_was = False

    def poll(self):
        """Return (shaken: bool, face_down: bool, pet_delta: int) for this tick."""
        shaken = False
        face_down = False
        if self._lis is not None:
            try:
                shaken = self._lis.shake(shake_threshold=_SHAKE_THRESHOLD)
                _x, _y, z = self._lis.acceleration
                face_down = z < _FACE_DOWN_Z
            except Exception:  # noqa: BLE001
                pass

        delta = 0
        if self._up is not None:
            up = not self._up.value      # active-low
            down = not self._down.value
            if up and not self._up_was:
                delta += 1
            if down and not self._down_was:
                delta -= 1
            self._up_was = up
            self._down_was = down

        return shaken, face_down, delta
