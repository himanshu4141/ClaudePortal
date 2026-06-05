"""Host shim for CircuitPython's `microcontroller` module.

`nvm` is a small bytearray so PetSelector can persist the chosen pet index.
It does NOT survive between emulator runs (no backing file) -- that's fine; the
device persists across reboots, the emulator just needs the API to exist.
"""

nvm = bytearray(64)
