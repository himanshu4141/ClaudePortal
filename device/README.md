# device

CircuitPython firmware for the Adafruit Matrix Portal M4. Subscribes to
Adafruit IO MQTT and renders three rotating screens on the 64×32 LED matrix
with a pixel-art Claude Code mascot.

## Install

1. Flash CircuitPython 9.x onto the board — see [`../docs/setup.md`](../docs/setup.md).
2. Install the required libraries onto `CIRCUITPY/lib/`. The full list is in
   [`lib_requirements.txt`](lib_requirements.txt). With
   [`circup`](https://github.com/adafruit/circup):
   ```bash
   circup install adafruit_esp32spi adafruit_minimqtt adafruit_connection_manager \
                  adafruit_matrixportal adafruit_display_text
   ```
   > The Matrix Portal M4 uses `adafruit_esp32spi` for Wi-Fi — the native
   > `wifi`/`socketpool`/`ssl` modules are not available on this board in CP 9.x.
3. Copy `secrets.py.example` to the board as `secrets.py` and fill in your
   Wi-Fi credentials and Adafruit IO username + AIO key:
   ```bash
   cp secrets.py.example /Volumes/CIRCUITPY/secrets.py
   # edit the values on the board
   ```
4. Copy `code.py` to the board:
   ```bash
   cp code.py /Volumes/CIRCUITPY/code.py
   ```
5. Copy the helper modules and the sprite directory:
   ```bash
   cp display.py screens.py formatting.py mascot.py moods.py /Volumes/CIRCUITPY/
   cp -r sprites /Volumes/CIRCUITPY/sprites
   ```
   The `sprites/` folder ships the pre-built BMPs. To re-generate them after
   editing the pixel grids, run `python3 sprites/build_sprites.py`.
6. Open a serial console to watch the board (replace the path with your
   actual device — `ls /dev/tty.usbmodem*` on macOS):
   ```bash
   screen /dev/tty.usbmodem* 115200
   ```

## What you'll see

Until the first MQTT message arrives the panel shows a `claude / portal`
waiting splash. Once the agent publishes a snapshot, the board rotates two
screens every 5 seconds:

- **SESS** — 5-hour session window: % used as a colour-coded bar (amber →
  copper → pink as it fills), and the countdown until the window resets
  (e.g. `4h 21m`)
- **WEEK** — weekly limit: % used and time until the next configured reset
  (e.g. `6d 14h` or `2h 30m` on reset day)

The hero mascot reacts to the latest snapshot each tick:

| Signal | Hero shows |
|---|---|
| No data yet | (waiting splash) |
| `now.active=True` and `now.rate>0` | TYPING |
| `now.active=True` and no rate | THINK |
| `session.window_pct >= 85` | SWEAT |
| Crossed a weekly token milestone (1M / 5M / 10M) | HAPPY for 5 s |
| Otherwise | IDLE |

The hero blinks randomly every 3–6 seconds; the corner mascot mirrors the
blink and tracks eye direction while TYPING or THINKING.

The serial console still prints the same one-line summaries from PR 5 for
sanity-checking against the panel.

If `code.py` raises, the top-level retry loop catches it, prints the error,
and reconnects with exponential backoff (5s → 10s → … → 60s).

## Roadmap

- **PR 5** (this) — Wi-Fi + MQTT bootstrap, prints snapshot to serial
- **PR 6** — 3-screen rotation (static text)
- **PR 7** — Mascot sprites + corner logo
- **PR 8** — Animations + mood state machine

See the top-level [`README.md`](../README.md) for project context.
