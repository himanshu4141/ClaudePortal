#!/usr/bin/env python3
"""Publish canned snapshots to Adafruit IO to exercise the panel without real usage.

Drives the same feed the agent publishes to, using the pinned sample payloads in
device/snapshot_schema.py. Lets you watch every derivable buddy state (idle, busy,
attention, level-up celebrate) on real hardware deterministically.

    ADAFRUIT_IO_USERNAME=... ADAFRUIT_IO_KEY=... python3 tools/mock_publish.py
    python3 tools/mock_publish.py busy            # one fixed sample, repeated
    python3 tools/mock_publish.py --interval 10   # cycle all samples every 10s
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "device"))
import snapshot_schema as ss  # noqa: E402

import paho.mqtt.client as mqtt  # noqa: E402

HOST = "io.adafruit.com"
PORT = 8883
FEED = "claude-portal.snapshot"


def main(argv: list[str]) -> int:
    username = os.environ.get("ADAFRUIT_IO_USERNAME")
    key = os.environ.get("ADAFRUIT_IO_KEY")
    if not username or not key:
        print("set ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY")
        return 1

    interval = 8
    fixed = None
    args = list(argv)
    if "--interval" in args:
        i = args.index("--interval")
        interval = int(args[i + 1])
        del args[i:i + 2]
    if args:
        fixed = args[0]
        if fixed not in ss.SAMPLES:
            print("unknown sample {!r}; choose from {}".format(fixed, list(ss.SAMPLES)))
            return 1

    topic = "{}/feeds/{}".format(username, FEED)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(username, key)
    client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
    client.connect(HOST, PORT, keepalive=60)
    client.loop_start()

    order = [fixed] if fixed else list(ss.SAMPLES)
    try:
        i = 0
        while True:
            name = order[i % len(order)]
            payload = json.dumps(ss.SAMPLES[name], separators=(",", ":"))
            client.publish(topic, payload, qos=1).wait_for_publish(timeout=10)
            print("published {!r} ({} bytes) -> {}".format(name, len(payload), topic))
            i += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        client.loop_stop()
        client.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
