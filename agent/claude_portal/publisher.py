from __future__ import annotations

import json
import logging
import os
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt

from .aggregator import Snapshot, aggregate
from .parser import DEFAULT_CLAUDE_ROOT, parse_all

ADAFRUIT_IO_HOST = "io.adafruit.com"
ADAFRUIT_IO_PORT = 8883
DEFAULT_FEED = "claude-portal.snapshot"
DEFAULT_INTERVAL_SECONDS = 30
MAX_PAYLOAD_BYTES = 1024

logger = logging.getLogger(__name__)


@dataclass
class PublisherConfig:
    username: str
    key: str
    feed: str = DEFAULT_FEED
    host: str = ADAFRUIT_IO_HOST
    port: int = ADAFRUIT_IO_PORT
    interval: int = DEFAULT_INTERVAL_SECONDS
    week_reset_weekday: int = 4    # Friday (Mon=0 … Fri=4 … Sun=6)
    week_reset_hour: int = 0       # hour-of-day in week_reset_tz
    week_reset_tz: str = ""        # IANA tz name; empty = system local tz
    week_limit_tokens: int = 0     # 0 = not configured

    @property
    def week_reset_tzinfo(self):
        if not self.week_reset_tz:
            return None
        from zoneinfo import ZoneInfo
        return ZoneInfo(self.week_reset_tz)

    @classmethod
    def from_env(cls) -> PublisherConfig:
        username = os.environ.get("ADAFRUIT_IO_USERNAME")
        key = os.environ.get("ADAFRUIT_IO_KEY")
        if not username or not key:
            raise RuntimeError(
                "ADAFRUIT_IO_USERNAME and ADAFRUIT_IO_KEY must be set "
                "(see agent/.env.example)"
            )
        return cls(
            username=username,
            key=key,
            feed=os.environ.get("PUBLISHER_FEED", DEFAULT_FEED),
            interval=int(os.environ.get("PUBLISHER_INTERVAL", DEFAULT_INTERVAL_SECONDS)),
            week_reset_weekday=int(os.environ.get("WEEK_RESET_WEEKDAY", "4")),
            week_reset_hour=int(os.environ.get("WEEK_RESET_HOUR", "0")),
            week_reset_tz=os.environ.get("WEEK_RESET_TZ", ""),
            week_limit_tokens=int(os.environ.get("WEEK_LIMIT_TOKENS", "0")),
        )


def _minutes_until(dt: datetime | None, now: datetime) -> int | None:
    if dt is None:
        return None
    delta = dt - now
    return max(0, int(delta.total_seconds() / 60))


def snapshot_to_payload(snapshot: Snapshot) -> str:
    now_ts = snapshot.generated_at
    return json.dumps(
        {
            "ts": now_ts.isoformat(),
            "now": {
                "active": snapshot.now.active,
                "model": snapshot.now.model,
                "rate": snapshot.now.tokens_per_minute,
            },
            "session": {
                "window_pct": snapshot.today.window_pct,
                "resets_in_min": _minutes_until(snapshot.today.window_resets_at, now_ts),
            },
            "week": {
                "window_pct": snapshot.week.window_pct,
                "resets_in_min": _minutes_until(snapshot.week.resets_at, now_ts),
                "total": snapshot.week.total_tokens,
            },
        },
        separators=(",", ":"),
    )


class Publisher:
    def __init__(self, config: PublisherConfig, client: mqtt.Client | None = None):
        self.config = config
        self.client = client or self._build_client()

    def _build_client(self) -> mqtt.Client:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.username_pw_set(self.config.username, self.config.key)
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        return client

    def _on_connect(self, _client, _userdata, _flags, reason_code, _properties=None):
        if reason_code == 0:
            logger.info("connected to %s as %s", self.config.host, self.config.username)
        else:
            logger.error("connect failed: reason=%s", reason_code)

    def _on_disconnect(self, _client, _userdata, _flags, reason_code, _properties=None):
        logger.warning("disconnected: reason=%s", reason_code)

    @property
    def topic(self) -> str:
        return f"{self.config.username}/feeds/{self.config.feed}"

    def connect(self) -> None:
        self.client.connect(self.config.host, self.config.port, keepalive=60)
        self.client.loop_start()

    def publish(self, payload: str) -> None:
        if len(payload.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError(
                f"payload exceeds Adafruit IO's {MAX_PAYLOAD_BYTES}-byte limit"
            )
        info = self.client.publish(self.topic, payload, qos=1)
        info.wait_for_publish(timeout=10)

    def disconnect(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()


def run_loop(
    config: PublisherConfig,
    root: Path = DEFAULT_CLAUDE_ROOT,
    iterations: int | None = None,
    sleep_fn=time.sleep,
) -> None:
    pub = Publisher(config)
    pub.connect()
    try:
        i = 0
        while iterations is None or i < iterations:
            payload = snapshot_to_payload(aggregate(
                parse_all(root),
                week_reset_weekday=config.week_reset_weekday,
                week_reset_hour=config.week_reset_hour,
                week_reset_tz=config.week_reset_tzinfo,
                week_limit_tokens=config.week_limit_tokens,
            ))
            pub.publish(payload)
            logger.info("published %d bytes to %s", len(payload), pub.topic)
            i += 1
            if iterations is None or i < iterations:
                sleep_fn(config.interval)
    finally:
        pub.disconnect()
