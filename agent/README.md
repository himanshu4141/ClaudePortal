# agent

Python service that parses `~/.claude/projects/**/*.jsonl` and publishes
Claude Code usage metrics to Adafruit IO over MQTT.

Implementation lands across subsequent PRs:

- **PR 2** — JSONL parser
- **PR 3** — Metrics aggregator (now / today / week)
- **PR 4** — Adafruit IO MQTT publisher + runner

See the top-level [`README.md`](../README.md) for project context.
