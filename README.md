# ClaudePortal

Real-time Claude Code usage tracker on an Adafruit Matrix Portal M4 with a
64×32 RGB LED panel. A small laptop agent parses your local `~/.claude`
session logs and publishes metrics to Adafruit IO over MQTT; the LED panel
subscribes and renders rotating screens with live usage data and a
pixel-art Claude Code mascot.

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

Functional. Hardware is running on CircuitPython 9.2.x with `adafruit_esp32spi`
for Wi-Fi (native `wifi`/`socketpool` are not available on the Matrix Portal M4
in CP 9.x). MQTT connects to Adafruit IO on port 1883 (non-SSL; the ESP32
co-processor's SSL stack is unreliable at this firmware version).

## License

MIT — see [`LICENSE`](LICENSE).
