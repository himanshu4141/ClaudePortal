# agent

Python service that parses `~/.claude/projects/**/*.jsonl` and publishes
Claude Code usage metrics to Adafruit IO over MQTT.

## Install

Requires Python 3.10+.

```bash
cd agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Parse usage events (PR 2)

Dump every parsed event as one JSON object per line:

```bash
python -m claude_portal --limit 10
```

Point at a different root for testing:

```bash
python -m claude_portal --root /path/to/fake/claude/projects
```

## Aggregate to a snapshot (PR 3)

Compute the three metric blocks (now / today / week) the device renders:

```bash
python -m claude_portal --snapshot
```

Outputs JSON with `now`, `today`, and `week` sections — the same shape the
publisher sends over MQTT.

## Publish to Adafruit IO (PR 4)

1. Copy `.env.example` to `.env` and fill in your Adafruit IO username + AIO key.
2. Send one snapshot and exit (useful for testing):
   ```bash
   python -m claude_portal --publish-once
   ```
3. Or run the continuous loop (publishes every `PUBLISHER_INTERVAL` seconds,
   default 30):
   ```bash
   python -m claude_portal --publish
   ```

To run it as a background service, see [`deploy/README.md`](deploy/README.md)
for launchd (macOS) and systemd-user (Linux) templates.

The published payload is a compact JSON document; the device subscribes to
`{username}/feeds/claude-portal.snapshot` and renders it on the three screens.

## Tests

```bash
pytest
```

## Roadmap

- **PR 2** (this) — JSONL parser
- **PR 3** — Metrics aggregator (now / today / week)
- **PR 4** — Adafruit IO MQTT publisher + runner

See the top-level [`README.md`](../README.md) for project context.
