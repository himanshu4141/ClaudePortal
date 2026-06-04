# Setup

Step-by-step setup for the ClaudePortal hardware, accounts, and firmware.

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
3. The agent creates feeds automatically on first run. No manual setup needed.

## 3. CircuitPython on the Matrix Portal

The device code targets CircuitPython **9.x**. The board page at
circuitpython.org has moved to CP 10, so grab the latest 9.x UF2 from the
[Adafruit S3 archive](https://adafruit-circuit-python.s3.amazonaws.com/index.html?prefix=bin/matrixportal_m4/en_US/)
(sort by date, pick the highest `9.x.x` file).

1. Double-tap the reset button on the Matrix Portal — it mounts as `MATRIXBOOT`.
2. Drag the `.uf2` file onto the drive. The board reboots and remounts as `CIRCUITPY`.
3. Verify with a serial console (`screen /dev/tty.usbmodem* 115200` on macOS/Linux,
   or use [Mu](https://codewith.mu/) / Thonny). You should see the REPL prompt.

## 4. CircuitPython libraries

> **Why adafruit_esp32spi?** The Matrix Portal M4 runs CircuitPython on its
> SAMD51 chip and talks to an ESP32 co-processor for Wi-Fi. The native
> `wifi`/`socketpool`/`ssl` modules are not compiled into CP 9.x for this
> board — you must use the `adafruit_esp32spi` library instead.

Download the [CircuitPython 9.x library bundle](https://circuitpython.org/libraries).
From the `lib/` folder of the bundle, copy these to `CIRCUITPY/lib/`:

| Entry | Type | Why |
|---|---|---|
| `adafruit_esp32spi/` | folder | Wi-Fi via ESP32 co-processor (AirLift) |
| `adafruit_matrixportal/` | folder | RGB matrix display driver |
| `adafruit_portalbase/` | folder | required by adafruit_matrixportal |
| `adafruit_minimqtt/` | folder | MQTT client for Adafruit IO |
| `adafruit_display_text/` | folder | label widgets used by all screens |
| `adafruit_connection_manager.mpy` | file | socket manager required by minimqtt |
| `adafruit_ticks.mpy` | file | required by adafruit_minimqtt |
| `adafruit_requests.mpy` | file | required by adafruit_portalbase |

> **Not needed:** `adafruit_io/` and `adafruit_bitmap_font/` — the device
> speaks MQTT directly and uses the built-in `terminalio.FONT`.

The easiest way to install (with the board mounted as `CIRCUITPY`) is
[`circup`](https://github.com/adafruit/circup):

```bash
circup install adafruit_esp32spi adafruit_matrixportal adafruit_minimqtt \
               adafruit_display_text adafruit_connection_manager
```

## 5. Device files

Copy the firmware to `CIRCUITPY` (see `device/README.md` for the full list):

```bash
cp device/code.py device/display.py device/screens.py \
   device/formatting.py device/mascot.py device/moods.py /Volumes/CIRCUITPY/
cp device/secrets.py.example /Volumes/CIRCUITPY/secrets.py   # then edit it
cp -r device/sprites /Volumes/CIRCUITPY/sprites
```

## 6. Wi-Fi + Adafruit IO credentials

Edit `CIRCUITPY/secrets.py`:

```python
secrets = {
    "ssid": "your_2.4GHz_network",   # Matrix Portal M4 is 2.4 GHz only
    "password": "your_password",
    "aio_username": "your_adafruit_io_username",
    "aio_key": "your_aio_key",
}
```

## 7. Python environment (for the agent)

Python 3.10+ on the machine where Claude Code runs:

```bash
cd agent/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY
```

Key `.env` settings:

| Variable | Default | Notes |
|---|---|---|
| `CLAUDE_PLAN` | — | `pro`, `max5`, or `max20` — sets session/weekly limits |
| `SESSION_LIMIT_TOKENS` | 0 (hidden) | Override plan default (Sonnet-equivalent tokens) |
| `WEEK_LIMIT_TOKENS` | 0 (hidden) | Override plan default |
| `OPUS_WEIGHT` | `1.67` | Anthropic counts Opus tokens ~1.67× vs Sonnet |
| `HAIKU_WEIGHT` | `0.33` | Anthropic counts Haiku tokens ~0.33× vs Sonnet |
| `WEEK_RESET_WEEKDAY` | `4` (Friday) | Day your billing week resets |
| `WEEK_RESET_HOUR` | `0` | Hour of reset in `WEEK_RESET_TZ` |
| `WEEK_RESET_TZ` | system tz | IANA timezone for weekly reset |

If the device's session % is consistently lower than Claude.ai when using Opus
heavily, adjust `OPUS_WEIGHT` — see `agent/README.md` for calibration steps.

## Troubleshooting

**Board doesn't appear as `CIRCUITPY`**
Double-tap reset. If it shows as `MATRIXBOOT`, the firmware didn't flash — try the UF2 again.

**Garbled pixels on the matrix**
Check the IDC ribbon orientation and that the external power supply is connected
(the matrix draws more current than USB can supply at full brightness).

**Wi-Fi won't connect / "No such ssid" error**
Confirm your network is 2.4 GHz — some routers broadcast 2.4 and 5 GHz under
the same SSID. The "No such ssid" message on first scan is transient; the code
retries and will connect.

**MQTT "Repeated connect failures" on retry**
The ESP32 co-processor socket state goes stale after a dropped connection.
`code.py` resets the ESP32 (`_esp.reset()`) before each retry, which clears it.
If you see this loop more than 2–3 times, power-cycle the board.

**MQTT connects but messages never arrive**
The device subscribes to `<username>/feeds/claude-portal.snapshot`. Confirm
the agent is running (`python -m claude_portal` in `agent/`) and check
Adafruit IO's feed page to see if payloads are arriving there first.
