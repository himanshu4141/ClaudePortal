# emulator

Run the ClaudePortal device firmware on your laptop. The actual `device/`
modules — `display.py`, `screens.py`, `mascot.py`, `moods.py`, `formatting.py` —
import unchanged through a thin set of host-side shims for the CircuitPython
modules they depend on (`wifi`, `socketpool`, `displayio`, `terminalio`,
`adafruit_minimqtt`, `adafruit_matrixportal`, `adafruit_display_text`).

A Tk window displays the emulated 64×32 panel scaled up so you can see pixels.
Use it to validate the agent → MQTT → device path end-to-end before plugging
into hardware.

## Install

Requires Python 3.10+ and Tk (already installed on macOS and most Linux
desktops; on headless Linux: `apt install python3-tk`).

```bash
cd emulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Offline mode (no MQTT)

Render a fixed snapshot from `snapshots/` and let the mascot animate on top
of it. No credentials needed.

```bash
python run.py --snapshot snapshots/active_session.json
python run.py --snapshot snapshots/sweating.json
```

The mascot still ticks (random blinks, mood derived from the snapshot), so
even a static snapshot shows the animation behavior.

## Live mode (subscribe to Adafruit IO)

Copy `.env.example` to `.env` (or reuse `agent/.env` — the emulator reads
both) with your Adafruit IO username + AIO key. Then:

```bash
python run.py --mqtt
```

The window stays on the waiting splash until the agent publishes a snapshot.
After that, screens rotate every 5 s and the mascot reacts to live data.

## How it works

```
emulator/
  shim/                          host stand-ins for CircuitPython modules
    wifi.py                      pretend-connected radio
    socketpool.py                no-op pool (the MQTT shim doesn't need it)
    terminalio.py                FONT sentinel
    displayio.py                 Group / Bitmap / Palette / TileGrid /
                                 OnDiskBitmap (parses our 1-bpp BMP sprites)
    adafruit_display_text/       Label class (text + xy + color)
    adafruit_matrixportal/       Matrix() returns a host display
    adafruit_minimqtt/           paho-mqtt wrapper with the device API
  renderer.py                    walks the displayio tree -> 64x32 PIL image
  viewer.py                      Tk window @ ~12x pixel scale
  run.py                         entrypoint: sys.path setup + main loop
  snapshots/                     example payloads matching the publisher
```

`run.py` puts `emulator/shim/` first on `sys.path`, then `emulator/`, then
`device/`. When the device modules do `import wifi` etc. they find the shims
instead of failing on missing CircuitPython modules. Everything else (logic,
sprite loading, mood state machine) is the real device code.

## Limitations

- Text uses PIL's default font, which is denser than terminalio.FONT, so
  labels look slightly tighter than they will on hardware. The pixel layout
  of bars and sprites is exact.
- The MQTT shim uses `paho-mqtt.loop(timeout=...)` (blocking) on a background
  thread instead of the device's single-threaded `adafruit_minimqtt.loop()`.
  Behavior matches; threading model differs.
- No display refresh timing / brightness modeling. We just composite the
  current state on each frame at the requested FPS.

## Troubleshooting

- **`ModuleNotFoundError: display` etc.** — run from inside `emulator/` so
  `run.py` can locate the `device/` directory at `../device/`.
- **`_tkinter.TclError: no display name`** — Tk needs a display. On a
  headless box, use `--snapshot ...` and edit `run.py` to call
  `img.save(...)` instead of `viewer.update_image(...)` (or run under XQuartz
  / WSLg).
- **MQTT connects but no messages arrive** — verify the agent is running
  (`python -m claude_portal --publish` from `agent/`) and the credentials in
  both `.env` files match.
