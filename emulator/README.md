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

Requires Python 3.10+ **built with Tcl/Tk support**. Most Linux distros ship
their system Python with Tk; macOS is more variable. See
[Python + Tk on macOS](#python--tk-on-macos) below if you're on a Mac.

```bash
cd emulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -c "import tkinter; tkinter.Tk().withdraw(); print('tk ok')"
```

That last sanity check should print `tk ok` and exit. If you get
`ModuleNotFoundError: No module named '_tkinter'` or a hard process crash,
your Python wasn't built against a working Tk — see below.

### Python + Tk on macOS

The clean combination on macOS as of 2026:

```bash
brew install tcl-tk@8
pyenv uninstall <your-version>     # confirms before deleting
env \
  LDFLAGS="-L$(brew --prefix tcl-tk@8)/lib" \
  CPPFLAGS="-I$(brew --prefix tcl-tk@8)/include" \
  PKG_CONFIG_PATH="$(brew --prefix tcl-tk@8)/lib/pkgconfig" \
  PYTHON_CONFIGURE_OPTS="--with-tcltk-includes='-I$(brew --prefix tcl-tk@8)/include' --with-tcltk-libs='-L$(brew --prefix tcl-tk@8)/lib -ltcl8.6 -ltk8.6'" \
  pyenv install <your-version>
```

Two macOS-specific gotchas:

- **`/usr/bin/python3` is unreliable.** Apple ships a Python that's compiled
  against a future macOS SDK; you'll see crashes like
  `macOS 26 (2603) or later required, have instead 16 (1603)`. Use pyenv or
  Homebrew Python, never the system one, for this venv.
- **Brew's plain `tcl-tk` is 9.x and won't compile against Python 3.12.x's
  `_tkinter.c`.** You need the versioned `tcl-tk@8` formula instead.
  Symptom: `passing 'int *' to parameter of type 'Tcl_Size *'` during
  `pyenv install`.

After the rebuild, create the venv with the freshly-built Python:

```bash
~/.pyenv/versions/<your-version>/bin/python -m venv .venv
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

- Text renders with a TrueType monospace (Monaco on macOS, Menlo / Courier /
  DejaVu fallbacks) at 8 pt with anti-aliasing forced off (`Image.fontmode = "1"`).
  This is *close* to `terminalio.FONT` (6×12 pixel font on the device) but not
  identical — glyph widths and heights differ by a pixel or two. Bars and
  sprite pixel layout are exact.
- The MQTT shim uses `paho-mqtt.loop(timeout=...)` (blocking) on a background
  thread instead of the device's single-threaded `adafruit_minimqtt.loop()`.
  Behavior matches; threading model differs.
- No display refresh timing or LED brightness/gamma modelling — colours
  appear more saturated on the emulator than on hardware.

## Troubleshooting

- **`ModuleNotFoundError: display` etc.** — run from inside `emulator/` so
  `run.py` can locate the `device/` directory at `../device/`.
- **`_tkinter.TclError: no display name`** — Tk needs a display. On a
  headless box, use `--snapshot ...` and edit `run.py` to call
  `img.save(...)` instead of `viewer.update_image(...)` (or run under XQuartz
  / WSLg).
- **`ModuleNotFoundError: No module named '_tkinter'`** — your Python was
  built without Tk. See [Python + Tk on macOS](#python--tk-on-macos).
- **Process crashes immediately with `macOS 26 (2603) or later required`**
  — you're using `/usr/bin/python3`, which is broken on older macOS
  releases. Switch to pyenv or Homebrew Python.
- **Text labels look blurry / huge** — your Python's PIL fell back to
  `ImageFont.load_default()`. The emulator prints
  `emulator: using font ... at 8pt` on startup if it found a monospace; if
  you see `falling back to PIL default` instead, install a system mono font
  (any of Monaco, Menlo, Courier New, DejaVuSansMono).
- **MQTT connects but no messages arrive** — verify the agent is running
  (`python -m claude_portal --publish` from `agent/`) and the credentials in
  both `.env` files match.
