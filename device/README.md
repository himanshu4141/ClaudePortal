# device

CircuitPython firmware for the Adafruit Matrix Portal M4. Subscribes to
Adafruit IO MQTT feeds and renders three rotating screens on the 64×32 LED
matrix with a pixel-art Claude Code mascot.

Implementation lands across subsequent PRs:

- **PR 5** — Wi-Fi + MQTT bootstrap
- **PR 6** — 3-screen rotation (static)
- **PR 7** — Mascot sprites + corner logo
- **PR 8** — Animations + mood state machine

See the top-level [`README.md`](../README.md) for project context and
[`docs/setup.md`](../docs/setup.md) for hardware setup.
