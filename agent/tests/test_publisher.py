from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from claude_portal.aggregator import NowMetrics, Snapshot, TodayMetrics, WeekMetrics
from claude_portal.publisher import (
    MAX_PAYLOAD_BYTES,
    Publisher,
    PublisherConfig,
    snapshot_to_payload,
)


def make_snapshot() -> Snapshot:
    return Snapshot(
        generated_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        now=NowMetrics(
            active=True,
            model="claude-sonnet-4-6",
            session_id="abc",
            session_tokens=42_108,
            session_started=datetime(2026, 5, 14, 10, 37, tzinfo=timezone.utc),
            session_duration_minutes=83,
            tokens_per_minute=1234.5,
        ),
        today=TodayMetrics(
            total_tokens=1_240_000,
            estimated_cost_usd=4.82,
            window_tokens=620_000,
            window_pct=62.0,
            window_resets_at=datetime(2026, 5, 14, 17, 0, tzinfo=timezone.utc),
        ),
        week=WeekMetrics(
            total_tokens=7_800_000,
            opus_tokens=2_418_000,
            sonnet_tokens=5_382_000,
            opus_pct=31.0,
            sonnet_pct=69.0,
            window_pct=14.0,
            resets_at=datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc),
        ),
    )


def test_snapshot_to_payload_is_valid_json_with_expected_shape():
    payload = snapshot_to_payload(make_snapshot())
    data = json.loads(payload)
    assert set(data.keys()) == {"ts", "now", "session", "week"}
    assert set(data["now"].keys()) == {"active", "model", "rate"}
    assert set(data["session"].keys()) == {"window_pct", "resets_in_min"}
    assert set(data["week"].keys()) == {"window_pct", "resets_in_min", "total"}


def test_snapshot_to_payload_contains_metric_values():
    data = json.loads(snapshot_to_payload(make_snapshot()))
    assert data["now"]["active"] is True
    assert data["now"]["model"] == "claude-sonnet-4-6"
    assert data["session"]["window_pct"] == 62.0
    assert data["session"]["resets_in_min"] == 300  # 17:00 - 12:00 = 5h = 300 min
    assert data["week"]["window_pct"] == 14.0
    assert data["week"]["resets_in_min"] == 720    # 15 May 00:00 - 14 May 12:00 = 12h = 720 min
    assert data["week"]["total"] == 7_800_000


def test_snapshot_to_payload_is_compact():
    payload = snapshot_to_payload(make_snapshot())
    assert ", " not in payload
    assert ": " not in payload
    assert len(payload.encode("utf-8")) < MAX_PAYLOAD_BYTES


def test_publisher_config_from_env_requires_credentials(monkeypatch):
    monkeypatch.delenv("ADAFRUIT_IO_USERNAME", raising=False)
    monkeypatch.delenv("ADAFRUIT_IO_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ADAFRUIT_IO_USERNAME"):
        PublisherConfig.from_env()


def test_publisher_config_from_env_reads_overrides(monkeypatch):
    monkeypatch.setenv("ADAFRUIT_IO_USERNAME", "alice")
    monkeypatch.setenv("ADAFRUIT_IO_KEY", "aio_xyz")
    monkeypatch.setenv("PUBLISHER_FEED", "custom-feed")
    monkeypatch.setenv("PUBLISHER_INTERVAL", "10")
    monkeypatch.setenv("WEEK_RESET_WEEKDAY", "4")
    monkeypatch.setenv("WEEK_RESET_HOUR", "9")
    monkeypatch.setenv("WEEK_RESET_TZ", "Europe/Dublin")
    monkeypatch.setenv("WEEK_LIMIT_TOKENS", "50000000")
    config = PublisherConfig.from_env()
    assert config.username == "alice"
    assert config.key == "aio_xyz"
    assert config.feed == "custom-feed"
    assert config.interval == 10
    assert config.week_reset_weekday == 4
    assert config.week_reset_hour == 9
    assert config.week_reset_tz == "Europe/Dublin"
    assert config.week_limit_tokens == 50_000_000


def test_publisher_config_week_reset_tzinfo_resolves_iana_name(monkeypatch):
    from zoneinfo import ZoneInfo
    config = PublisherConfig(username="u", key="k", week_reset_tz="Europe/Dublin")
    assert config.week_reset_tzinfo == ZoneInfo("Europe/Dublin")


def test_publisher_config_week_reset_tzinfo_none_when_unset():
    config = PublisherConfig(username="u", key="k", week_reset_tz="")
    assert config.week_reset_tzinfo is None


def test_publisher_publishes_to_namespaced_topic():
    config = PublisherConfig(username="alice", key="k", feed="claude-portal.snapshot")
    fake_client = MagicMock()
    fake_info = MagicMock()
    fake_client.publish.return_value = fake_info

    pub = Publisher(config, client=fake_client)
    pub.publish('{"hello":1}')

    fake_client.publish.assert_called_once()
    topic, payload = fake_client.publish.call_args.args
    assert topic == "alice/feeds/claude-portal.snapshot"
    assert payload == '{"hello":1}'
    assert fake_client.publish.call_args.kwargs == {"qos": 1}
    fake_info.wait_for_publish.assert_called_once()


def test_publisher_rejects_oversized_payload():
    config = PublisherConfig(username="alice", key="k")
    pub = Publisher(config, client=MagicMock())
    with pytest.raises(ValueError, match="exceeds"):
        pub.publish("x" * (MAX_PAYLOAD_BYTES + 1))
