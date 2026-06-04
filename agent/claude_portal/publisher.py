from __future__ import annotations

import json
import logging
import os
import ssl
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import paho.mqtt.client as mqtt

from .aggregator import Snapshot, aggregate
from .parser import DEFAULT_CLAUDE_ROOT, parse_all

ADAFRUIT_IO_HOST = "io.adafruit.com"
ADAFRUIT_IO_PORT = 8883
DEFAULT_FEED = "claude-portal.snapshot"
DEFAULT_INTERVAL_SECONDS = 30
MAX_PAYLOAD_BYTES = 1024

logger = logging.getLogger(__name__)

# Calibrated against real Pro plan usage (in+out+cache_creation tokens).
# Pro session: observed limit hit at window_tokens=2,765,639; rounded up to 2,766,000.
# Pro week: 107,271,806 observed at 23% → 466M limit confirmed.
# Max5/Max20: assumed 5× / 20× Pro (community calibration data welcome).
# Override per-field with SESSION_LIMIT_TOKENS / WEEK_LIMIT_TOKENS in .env.
PLAN_LIMITS: dict[str, dict[str, int]] = {
    "pro": {
        "session":   2_766_000,
        "week":    466_000_000,
    },
    "max5": {
        "session":  13_830_000,   # 5× pro
        "week":  2_330_000_000,
    },
    "max20": {
        "session":  55_320_000,   # 20× pro
        "week":  9_320_000_000,
    },
}


@dataclass
class PublisherConfig:
    username: str
    key: str
    feed: str = DEFAULT_FEED
    host: str = ADAFRUIT_IO_HOST
    port: int = ADAFRUIT_IO_PORT
    interval: int = DEFAULT_INTERVAL_SECONDS
    session_limit_tokens: int = 0  # 0 = not configured
    week_reset_weekday: int = 4    # Friday (Mon=0 … Fri=4 … Sun=6)
    week_reset_hour: int = 0       # hour-of-day in week_reset_tz
    week_reset_tz: str = ""        # IANA tz name; empty = system local tz
    week_limit_tokens: int = 0     # 0 = not configured
    opus_weight: float = 1.0       # Opus token multiplier; set > 1.0 if Claude shows higher %

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
        plan = os.environ.get("CLAUDE_PLAN", "").lower().strip()
        plan_defaults = PLAN_LIMITS.get(plan, {})

        return cls(
            username=username,
            key=key,
            feed=os.environ.get("PUBLISHER_FEED", DEFAULT_FEED),
            interval=int(os.environ.get("PUBLISHER_INTERVAL", DEFAULT_INTERVAL_SECONDS)),
            session_limit_tokens=int(
                os.environ.get("SESSION_LIMIT_TOKENS", plan_defaults.get("session", 0))
            ),
            week_reset_weekday=int(os.environ.get("WEEK_RESET_WEEKDAY", "4")),
            week_reset_hour=int(os.environ.get("WEEK_RESET_HOUR", "0")),
            week_reset_tz=os.environ.get("WEEK_RESET_TZ", ""),
            week_limit_tokens=int(
                os.environ.get("WEEK_LIMIT_TOKENS", plan_defaults.get("week", 0))
            ),
            opus_weight=float(os.environ.get("OPUS_WEIGHT", "1.0")),
        )


def _minutes_until(dt: datetime | None, now: datetime) -> int | None:
    if dt is None:
        return None
    delta = dt - now
    return max(0, int(delta.total_seconds() / 60))


def snapshot_to_payload(snapshot: Snapshot) -> str:
    now_ts = snapshot.generated_at
    s = snapshot.session
    w = snapshot.week
    return json.dumps(
        {
            "ts": now_ts.isoformat(),
            "now": {
                "active": snapshot.now.active,
                "model": snapshot.now.model,
                "rate": snapshot.now.tokens_per_minute,
            },
            "session": {
                "window_pct": s.window_pct,
                "window_tokens": s.window_tokens,
                "resets_in_min": _minutes_until(s.window_resets_at, now_ts),
                "tok": {
                    "in": s.window_input_tokens,
                    "out": s.window_output_tokens,
                    "cw": s.window_cache_creation_tokens,
                    "cr": s.window_cache_read_tokens,
                },
            },
            "week": {
                "window_pct": w.window_pct,
                "resets_in_min": _minutes_until(w.resets_at, now_ts),
                "total": w.total_tokens,
                "tok": {
                    "in": w.input_tokens,
                    "out": w.output_tokens,
                    "cw": w.cache_creation_tokens,
                    "cr": w.cache_read_tokens,
                },
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
                window_limit_tokens=config.session_limit_tokens,
                week_reset_weekday=config.week_reset_weekday,
                week_reset_hour=config.week_reset_hour,
                week_reset_tz=config.week_reset_tzinfo,
                week_limit_tokens=config.week_limit_tokens,
                opus_weight=config.opus_weight,
            ))
            pub.publish(payload)
            logger.info("published %d bytes to %s", len(payload), pub.topic)
            i += 1
            if iterations is None or i < iterations:
                sleep_fn(config.interval)
    finally:
        pub.disconnect()
