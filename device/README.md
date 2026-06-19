# device

CircuitPython firmware for the Adafruit Matrix Portal M4. Subscribes to
Adafruit IO MQTT and renders an animated **desk-pet buddy** on the 64×32 LED
matrix, with the weekly-limit screen as a secondary view. Inspired by
[claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy) —
ported to this ambient LED panel, minus the BLE back-channel (no approve/deny).

## Install

1. Flash CircuitPython 9.x onto the board — see [`../docs/setup.md`](../docs/setup.md).
2. Install the required libraries onto `CIRCUITPY/lib/`. The full list is in
   [`lib_requirements.txt`](lib_requirements.txt). With
   [`circup`](https://github.com/adafruit/circup):
   ```bash
   circup install adafruit_esp32spi adafruit_minimqtt adafruit_connection_manager \
                  adafruit_matrixportal adafruit_display_text adafruit_lis3dh
   ```
   > The Matrix Portal M4 uses `adafruit_esp32spi` for Wi-Fi — the native
   > `wifi`/`socketpool`/`ssl` modules are not available on this board in CP 9.x.
   > `adafruit_lis3dh` drives the onboard accelerometer (shake / face-down).
3. Copy `secrets.py.example` to the board as `secrets.py` and fill in Wi-Fi +
   Adafruit IO credentials.
4. Copy the firmware to the board:
   ```bash
   cp code.py display.py screens.py formatting.py /Volumes/CIRCUITPY/
   cp buddy.py buddy_controller.py buddy_state.py glyphs.py inputs.py snapshot_schema.py /Volumes/CIRCUITPY/
   cp mascot.py /Volumes/CIRCUITPY/                 # still used by the WEEK screen
   cp -r pets /Volumes/CIRCUITPY/pets
   ```
   The pet character data in `pets/` is auto-generated — see
   [`../docs/buddy.md`](../docs/buddy.md).
5. Open a serial console (`ls /dev/tty.usbmodem*` on macOS):
   ```bash
   screen /dev/tty.usbmodem* 115200
   ```

## What you'll see

Until the first MQTT message arrives the panel shows a `claude / portal`
waiting splash. Once the agent publishes a snapshot, a pixel pet animates as the
primary screen (~20 s) and rotates with the **WEEK** limit screen (~6 s).

The pet's state is derived entirely device-side from the snapshot + physical
input — no back-channel:

| Pet state | Trigger |
|---|---|
| sleep | no snapshot within 90 s (agent offline) |
| idle | `now.active == False` |
| busy | `now.active == True` |
| attention | `session.window_pct >= 85` (limit warning) |
| celebrate | leveled up (every 250 K weekly tokens) |
| dizzy | board **shaken** |
| nap | board **face-down** (energy recharges) → **heart** on wake |

The bottom two rows are ambient bars: **session window %** (green→amber→red) and
**energy**. Press **UP / DOWN** to cycle the pet — the choice persists in NVM.

If `code.py` raises, the top-level retry loop catches it, prints the error, and
reconnects with exponential backoff (5 s → 10 s → … → 60 s).

## Testing without hardware

Host unit tests (pure-Python logic) run under pytest:
```bash
python3 -m pytest device/tests -q
```
To drive a real panel with canned states (no real Claude usage), see
`tools/mock_publish.py`.

See [`../docs/buddy.md`](../docs/buddy.md) for architecture and the pet-porting
pipeline, and the top-level [`README.md`](../README.md) for project context.
