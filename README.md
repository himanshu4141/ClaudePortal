# ClaudePortal

Real-time Claude Code usage tracker on an Adafruit Matrix Portal M4 with a
64×32 RGB LED panel. A small laptop agent parses your local `~/.claude`
session logs and publishes metrics to Adafruit IO over MQTT; the LED panel
subscribes and renders an animated **desk-pet buddy** that reacts to your
usage, alongside a weekly-limit screen.

The buddy is a port of
[claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy) onto
this ambient LED panel — minus the BLE back-channel (no approve/deny). See
[`docs/buddy.md`](docs/buddy.md).

## Hardware

- [Adafruit Matrix Portal M4 starter kit](https://www.adafruit.com/product/4812)
- 64×32 RGB LED matrix (included in the kit, 4mm pitch)
- USB-C power
- 2.4 GHz Wi-Fi network

## Architecture

```
~/.claude/projects/**/*.jsonl
            │
            ▼
   ┌────────────────┐   every 30s    ┌──────────────┐   MQTT      ┌─────────────┐
   │  agent (Python)│ ─────────────▶ │  Adafruit IO │ ──────────▶ │ Matrix      │
   │  parse + agg.  │                │  (5 feeds)   │             │ Portal M4   │
   └────────────────┘                └──────────────┘             └─────────────┘
```

The agent runs on the machine where Claude Code runs. The Matrix Portal only
needs Wi-Fi credentials and Adafruit IO keys — it never sees the raw JSONL.

## Repo layout

```
agent/        Python service: parse JSONL, aggregate, publish to Adafruit IO
device/       CircuitPython firmware for the Matrix Portal M4
docs/         Setup and hardware notes
```

## Quick start

See [`docs/setup.md`](docs/setup.md) for hardware setup, Adafruit IO account
creation, CircuitPython flashing, and library installation.

## Status

Functional. The primary screen is an animated pixel pet that reacts to your
usage (idle / busy / limit-warning / celebrate on level-up), responds to a
**shake** (dizzy) and being set **face-down** (nap), and can be swapped with the
**UP/DOWN** buttons (6 species, choice persisted). It rotates with a **WEEK**
screen (weekly % + next reset countdown). The bottom rows show ambient
session-window % and energy bars. See [`docs/buddy.md`](docs/buddy.md).

Hardware runs CircuitPython 9.2.x with `adafruit_esp32spi` for Wi-Fi (native
`wifi`/`socketpool` are not available on the Matrix Portal M4 in CP 9.x).
MQTT connects to Adafruit IO on port 1883 (non-SSL; the ESP32 co-processor's
TLS stack is unreliable at this firmware version).

## License

MIT — see [`LICENSE`](LICENSE).
