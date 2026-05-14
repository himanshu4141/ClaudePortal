# Setup

Step-by-step setup for the ClaudePortal hardware and accounts. Software setup
for the agent and device is covered in `agent/README.md` and `device/README.md`
respectively, once those components land.

## 1. Hardware assembly

You'll need the [Adafruit Matrix Portal M4 starter kit](https://www.adafruit.com/product/4812),
which includes:

- Matrix Portal M4 board
- 64×32 RGB LED matrix (4mm pitch)
- Power supply
- USB-C cable
- Mounting hardware

Assembly:

1. Plug the Matrix Portal directly into the matrix's IDC connector — the
   board is keyed and only fits one way.
2. Secure with the included standoffs / acrylic frame if using the kit's
   mount.
3. Connect the power supply to the matrix's power lead (do **not** rely on
   USB alone to power the matrix at full brightness).
4. Connect USB-C from the Matrix Portal to your computer for flashing.

## 2. Adafruit IO account

1. Sign up at [io.adafruit.com](https://io.adafruit.com/). The free tier is
   sufficient: 30 data points/min, 30-day history, 10 feeds.
2. From your profile, copy your **Username** and **AIO Key** — you'll need
   both for the agent and device.
3. We'll create the feeds programmatically from the agent in PR 4. No manual
   setup needed yet.

## 3. CircuitPython on the Matrix Portal

1. Download the latest CircuitPython 9.x UF2 for the Matrix Portal M4:
   [https://circuitpython.org/board/matrixportal_m4/](https://circuitpython.org/board/matrixportal_m4/)
2. Double-tap the reset button on the Matrix Portal — it'll mount as
   `MATRIXBOOT`.
3. Drag the `.uf2` file onto the drive. The board reboots and remounts as
   `CIRCUITPY`.
4. Verify by opening a serial console (`screen /dev/tty.usbmodem* 115200`
   on macOS/Linux, or use [Mu](https://codewith.mu/) / Thonny). You should
   see the REPL prompt.

## 4. CircuitPython libraries

Download the [CircuitPython library bundle](https://circuitpython.org/libraries)
for version 9.x. From the `lib/` folder of the bundle, copy these to the
`CIRCUITPY/lib/` directory on the board:

- `adafruit_matrixportal/` (folder)
- `adafruit_minimqtt/` (folder)
- `adafruit_io/` (folder)
- `adafruit_bitmap_font/` (folder)
- `adafruit_display_text/` (folder)
- `adafruit_connection_manager.mpy`
- `adafruit_requests.mpy`
- `adafruit_ticks.mpy`

Exact list will be pinned in `device/README.md` when device PRs land.

## 5. Wi-Fi credentials

You'll provide your SSID and password in `device/secrets.py` (template
provided in PR 5). The Matrix Portal M4 only supports **2.4 GHz** Wi-Fi —
5 GHz networks won't be visible.

## 6. Python environment (for the agent)

Python 3.10 or newer on the machine where Claude Code runs. The agent will
ship a `requirements.txt` in PR 2. Create a venv to keep things tidy:

```bash
cd agent/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Troubleshooting

- **Matrix Portal doesn't show up as `CIRCUITPY`:** double-tap reset; if it
  shows as `MATRIXBOOT`, the firmware didn't flash. Try the UF2 again.
- **Matrix shows garbled pixels:** check the IDC ribbon orientation and that
  the matrix power supply is connected.
- **Wi-Fi won't connect:** confirm 2.4 GHz; some routers hide 2.4 by default
  under a single SSID.
