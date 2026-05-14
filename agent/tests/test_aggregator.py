from __future__ import annotations

from datetime import datetime, timedelta, timezone

from claude_portal.aggregator import aggregate
from claude_portal.models import UsageEvent

UTC = timezone.utc
NOW = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)  # Thursday noon


def make_event(
    ts: datetime,
    *,
    model: str = "claude-sonnet-4-6",
    session: str = "s1",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0,
) -> UsageEvent:
    return UsageEvent(
        timestamp=ts,
        session_id=session,
        project_path="/tmp/test",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
    )


def test_aggregate_empty_returns_zero_snapshot():
    snap = aggregate([], now=NOW, tz=UTC)
    assert snap.now.active is False
    assert snap.now.session_tokens == 0
    assert snap.today.total_tokens == 0
    assert snap.today.window_pct == 0.0
    assert snap.week.total_tokens == 0
    assert snap.week.per_day_tokens == [0] * 7


def test_now_active_when_latest_within_threshold():
    events = [
        make_event(NOW - timedelta(minutes=10), input_tokens=100, output_tokens=200),
        make_event(NOW - timedelta(minutes=2), input_tokens=50, output_tokens=100),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.now.active is True
    assert snap.now.session_tokens == 450
    assert snap.now.model == "claude-sonnet-4-6"
    assert snap.now.session_id == "s1"


def test_now_inactive_when_latest_too_old():
    events = [make_event(NOW - timedelta(minutes=30), input_tokens=100, output_tokens=200)]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.now.active is False


def test_now_only_counts_current_session_tokens():
    events = [
        make_event(NOW - timedelta(hours=2), session="old", input_tokens=999),
        make_event(NOW - timedelta(minutes=10), session="new", input_tokens=100),
        make_event(NOW - timedelta(minutes=2), session="new", input_tokens=50),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.now.session_id == "new"
    assert snap.now.session_tokens == 150


def test_now_tokens_per_minute_uses_5min_window():
    events = [
        make_event(NOW - timedelta(minutes=30), input_tokens=10_000),  # outside rate window
        make_event(NOW - timedelta(minutes=1), input_tokens=600),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.now.tokens_per_minute == 120.0  # 600 / 5


def test_today_window_pct_against_limit():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=2_000_000)]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.today.window_tokens == 2_000_000
    assert snap.today.window_pct == 10.0


def test_today_window_pct_capped_at_100():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=50_000_000)]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.today.window_pct == 100.0


def test_today_excludes_events_outside_5h_window():
    events = [
        make_event(NOW - timedelta(hours=10), input_tokens=999_999),
        make_event(NOW - timedelta(hours=1), input_tokens=500_000),
    ]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.today.window_tokens == 500_000


def test_today_cost_estimate_sonnet():
    today_morning = NOW.replace(hour=10)
    events = [
        make_event(
            today_morning,
            model="claude-sonnet-4-6",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert abs(snap.today.estimated_cost_usd - 18.00) < 0.01  # 3 + 15


def test_today_cost_estimate_opus():
    today_morning = NOW.replace(hour=10)
    events = [
        make_event(
            today_morning,
            model="claude-opus-4-7",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert abs(snap.today.estimated_cost_usd - 90.00) < 0.01  # 15 + 75


def test_week_per_day_breakdown():
    events = [
        make_event(NOW - timedelta(days=6, hours=2), input_tokens=100),
        make_event(NOW - timedelta(days=2, hours=1), input_tokens=200),
        make_event(NOW - timedelta(hours=1), input_tokens=300),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.per_day_tokens[0] == 100
    assert snap.week.per_day_tokens[4] == 200
    assert snap.week.per_day_tokens[6] == 300
    assert snap.week.total_tokens == 600


def test_week_drops_events_older_than_seven_days():
    events = [
        make_event(NOW - timedelta(days=8), input_tokens=9999),
        make_event(NOW - timedelta(hours=1), input_tokens=100),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.total_tokens == 100


def test_week_model_split_opus_vs_sonnet():
    events = [
        make_event(NOW - timedelta(hours=1), model="claude-opus-4-7", input_tokens=300),
        make_event(NOW - timedelta(hours=1), model="claude-sonnet-4-6", input_tokens=700),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.opus_tokens == 300
    assert snap.week.sonnet_tokens == 700
    assert snap.week.opus_pct == 30.0
    assert snap.week.sonnet_pct == 70.0


def test_week_labels_are_seven_day_initials_ending_today():
    snap = aggregate([], now=NOW, tz=UTC)
    assert len(snap.week.per_day_labels) == 7
    # Thursday is "T", so labels end with "T" for 2026-05-14
    assert snap.week.per_day_labels[-1] == "T"


def test_window_resets_at_is_oldest_in_window_plus_5h():
    oldest = NOW - timedelta(hours=3)
    events = [
        make_event(oldest, input_tokens=100),
        make_event(NOW - timedelta(minutes=10), input_tokens=200),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.today.window_resets_at == oldest + timedelta(hours=5)
