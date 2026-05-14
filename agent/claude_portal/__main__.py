from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from .aggregator import aggregate
from .parser import DEFAULT_CLAUDE_ROOT, parse_all
from .publisher import Publisher, PublisherConfig, run_loop, snapshot_to_payload


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Parse, aggregate, and optionally publish Claude Code usage to Adafruit IO.",
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_CLAUDE_ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--snapshot",
        action="store_true",
        help="Print one aggregated snapshot.",
    )
    mode.add_argument(
        "--publish",
        action="store_true",
        help="Publish snapshots to Adafruit IO continuously.",
    )
    mode.add_argument(
        "--publish-once",
        action="store_true",
        help="Publish a single snapshot and exit.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap event count in default mode.",
    )
    args = parser.parse_args(argv)

    if args.publish or args.publish_once:
        config = PublisherConfig.from_env()
        if args.publish_once:
            _publish_once(config, args.root)
        else:
            run_loop(config, root=args.root)
        return 0

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


def _publish_once(config: PublisherConfig, root: Path) -> None:
    pub = Publisher(config)
    pub.connect()
    try:
        payload = snapshot_to_payload(aggregate(parse_all(root)))
        pub.publish(payload)
    finally:
        pub.disconnect()


if __name__ == "__main__":
    raise SystemExit(main())
