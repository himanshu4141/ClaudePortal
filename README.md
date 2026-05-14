# ClaudePortal

Real-time Claude Code usage tracker on an Adafruit Matrix Portal M4 with a
64×32 RGB LED panel. A small laptop agent parses your local `~/.claude`
session logs and publishes metrics to Adafruit IO over MQTT; the LED panel
subscribes and renders three rotating screens (now / today / week) with a
pixel-art mascot.

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

Early development. See PR history for the build progression:

1. Scaffold
2. JSONL parser
3. Metrics aggregator
4. Adafruit IO publisher
5. Device bootstrap (Wi-Fi + MQTT)
6. Static screen rotation
7. Mascot sprites
8. Animations + mood state machine

## License

MIT — see [`LICENSE`](LICENSE).
