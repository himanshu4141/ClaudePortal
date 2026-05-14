from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .aggregator import aggregate
from .parser import DEFAULT_CLAUDE_ROOT, parse_all


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Parse Claude Code session JSONL files and emit usage data as JSON.",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_CLAUDE_ROOT)
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Emit one aggregated snapshot instead of per-event records.",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args(argv)

    if args.snapshot:
        snapshot = aggregate(parse_all(args.root))
        json.dump(asdict(snapshot), sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return 0

    count = 0
    for event in parse_all(args.root):
        record = asdict(event)
        record["timestamp"] = event.timestamp.isoformat()
        json.dump(record, sys.stdout)
        sys.stdout.write("\n")
        count += 1
        if args.limit and count >= args.limit:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
