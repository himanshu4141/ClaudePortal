from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from .models import UsageEvent

DEFAULT_CLAUDE_ROOT = Path.home() / ".claude" / "projects"


def discover_jsonl_files(root: Path | None = None) -> Iterator[Path]:
    root = root or DEFAULT_CLAUDE_ROOT
    if not root.exists():
        return
    yield from sorted(root.rglob("*.jsonl"))


def parse_file(path: Path) -> Iterator[UsageEvent]:
    # Claude Code writes each assistant message 2-5× to the JSONL (same message.id,
    # slightly different timestamps). Deduplicate on message.id within each file.
    seen_message_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("type") == "assistant":
                msg_id = (data.get("message") or {}).get("id", "")
                if msg_id:
                    if msg_id in seen_message_ids:
                        continue
                    seen_message_ids.add(msg_id)
            event = _to_event(data, path)
            if event is not None:
                yield event


def parse_all(root: Path | None = None) -> Iterator[UsageEvent]:
    for path in discover_jsonl_files(root):
        yield from parse_file(path)


def decode_project_path(encoded: str) -> str:
    # Claude Code encodes /Users/foo/bar as -Users-foo-bar in the directory name.
    if encoded.startswith("-"):
        return "/" + encoded[1:].replace("-", "/")
    return encoded.replace("-", "/")


def _to_event(data: dict, path: Path) -> UsageEvent | None:
    event_type = data.get("type")
    timestamp_str = data.get("timestamp")
    if not isinstance(timestamp_str, str):
        return None
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
    except ValueError:
        return None

    # Context compaction boundary: marks the start of a fresh rate-limit window.
    # Claude.ai resets the session counter here, so we use it as the effective
    # session start when computing the session usage percentage.
    if event_type == "system" and data.get("subtype") == "compact_boundary":
        sid = data.get("sessionId") or path.stem
        return UsageEvent(
            timestamp=ts,
            session_id=str(sid),
            project_path=decode_project_path(path.parent.name),
            model="",
            input_tokens=0,
            output_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            is_compact_boundary=True,
        )

    if event_type != "assistant":
        return None
    message = data.get("message") or {}
    usage = message.get("usage")
    if not isinstance(usage, dict):
        return None
    return UsageEvent(
        timestamp=ts,
        session_id=path.stem,
        project_path=decode_project_path(path.parent.name),
        model=str(message.get("model") or "unknown"),
        input_tokens=_int(usage.get("input_tokens")),
        output_tokens=_int(usage.get("output_tokens")),
        cache_creation_tokens=_int(usage.get("cache_creation_input_tokens")),
        cache_read_tokens=_int(usage.get("cache_read_input_tokens")),
    )


def _int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
