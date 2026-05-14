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
   circup install adafruit_minimqtt adafruit_connection_manager
   ```
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
5. Open a serial console to watch the board (replace the path with your
   actual device — `ls /dev/tty.usbmodem*` on macOS):
   ```bash
   screen /dev/tty.usbmodem* 115200
   ```

## What you'll see (PR 5)

This PR is just the network bootstrap. Expected serial output:

```
wifi: connecting to MyNetwork
wifi: ip=192.168.1.42
mqtt: connected rc=0
mqtt: subscribed to your-username/feeds/claude-portal.snapshot
mqtt: msg topic=your-username/feeds/claude-portal.snapshot bytes=247
  NOW   active=True model=claude-sonnet-4-6 tokens=42108 rate=1234.5/min
  TODAY tokens=1240000 cost=$4.82 window=62.0%
  WEEK  total=7800000 opus=31.0% sonnet=69.0%
```

The LED matrix itself stays dark until PR 6.

If `code.py` raises, the top-level retry loop catches it, prints the error,
and reconnects with exponential backoff (5s → 10s → … → 60s).

## Roadmap

- **PR 5** (this) — Wi-Fi + MQTT bootstrap, prints snapshot to serial
- **PR 6** — 3-screen rotation (static text)
- **PR 7** — Mascot sprites + corner logo
- **PR 8** — Animations + mood state machine

See the top-level [`README.md`](../README.md) for project context.
