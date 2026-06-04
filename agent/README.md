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

## Parse usage events

Dump every parsed event as one JSON object per line:

```bash
python -m claude_portal --limit 10
```

Point at a different root for testing:

```bash
python -m claude_portal --root /path/to/fake/claude/projects
```

## Aggregate to a snapshot

Compute the three metric blocks (now / session / week) the device renders:

```bash
python -m claude_portal --snapshot
```

Outputs JSON with `now`, `session`, and `week` sections — the same shape the
publisher sends over MQTT.

## Publish to Adafruit IO

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

## How session % is computed

The agent aggregates all active Claude Code sessions (all JSONL files modified
in the last 5 hours) into a single rate-limit view. Key design decisions:

- **Global pool**: Anthropic's 5h rate limit is per API key, shared across all
  concurrent Claude Code windows. The agent sums tokens across all sessions.
- **No compact filtering**: a `/compact` command resets the visible conversation
  context but does **not** reset the underlying rate-limit counter. Pre-compact
  tokens still count until they age out of the 5h rolling window.
- **Message-ID deduplication**: Claude Code writes each API response 2–5× to
  the JSONL. The parser deduplicates on `message.id` to avoid a ~2.8× overcount.
- **Model weights**: Anthropic counts tokens proportionally to compute cost.
  Default weights: Opus = 1.67×, Sonnet = 1.0×, Haiku = 0.33×. Override with
  `OPUS_WEIGHT` / `HAIKU_WEIGHT` in `.env` if you observe a consistent gap
  vs Claude.ai.

## Calibration

The `CLAUDE_PLAN` env var sets defaults for `SESSION_LIMIT_TOKENS` and
`WEEK_LIMIT_TOKENS`:

| Plan   | Session limit      | Weekly limit       |
|--------|--------------------|--------------------|
| `pro`  | 2,766,000 tokens   | 466,000,000 tokens |
| `max5` | 13,830,000 tokens  | 2,330,000,000 tokens (est.) |
| `max20`| 55,320,000 tokens  | 9,320,000,000 tokens (est.) |

Limits are in Sonnet-equivalent tokens (Opus usage is scaled by `OPUS_WEIGHT`
before comparing). The Pro session limit was calibrated by observing 100% at
2,765,639 tokens. Max5/Max20 limits are community estimates (5× / 20× Pro).

To calibrate from scratch:
1. Leave `SESSION_LIMIT_TOKENS` unset and restart the agent.
2. Note `SESSION tokens=N` in the serial console.
3. Check Claude.ai's usage panel for the percentage `P`.
4. Set `SESSION_LIMIT_TOKENS = N / (P / 100)`.

## Tests

```bash
pytest
```
