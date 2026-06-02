from __future__ import annotations

from datetime import datetime, timedelta, timezone

from claude_portal.aggregator import aggregate
from claude_portal.models import UsageEvent

UTC = timezone.utc
NOW = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)  # Thursday noon UTC


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
    assert snap.session.window_tokens == 0
    assert snap.session.window_pct == 0.0
    assert snap.week.total_tokens == 0
    assert snap.week.window_pct == 0.0
    assert snap.week.resets_at is not None


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


def test_session_window_pct_against_limit():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=2_000_000)]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.session.window_tokens == 2_000_000
    assert snap.session.window_pct == 10.0


def test_session_window_pct_capped_at_100():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=50_000_000)]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.session.window_pct == 100.0


def test_session_excludes_events_outside_5h_window():
    events = [
        make_event(NOW - timedelta(hours=10), input_tokens=999_999),
        make_event(NOW - timedelta(hours=1), input_tokens=500_000),
    ]
    snap = aggregate(events, now=NOW, window_limit_tokens=20_000_000, tz=UTC)
    assert snap.session.window_tokens == 500_000


def test_session_excludes_cache_read_tokens_from_window_count():
    events = [make_event(
        NOW - timedelta(hours=1),
        input_tokens=100,
        output_tokens=200,
        cache_creation_tokens=300,
        cache_read_tokens=1_000_000,  # large but excluded
    )]
    snap = aggregate(events, now=NOW, window_limit_tokens=10_000, tz=UTC)
    assert snap.session.window_tokens == 600        # 100+200+300
    assert snap.session.window_cache_read_tokens == 1_000_000
    assert snap.session.window_pct == 6.0           # 600/10000


def test_session_token_breakdown():
    events = [make_event(
        NOW - timedelta(hours=1),
        input_tokens=10,
        output_tokens=20,
        cache_creation_tokens=30,
        cache_read_tokens=40,
    )]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.session.window_input_tokens == 10
    assert snap.session.window_output_tokens == 20
    assert snap.session.window_cache_creation_tokens == 30
    assert snap.session.window_cache_read_tokens == 40
    assert snap.session.window_tokens == 60  # 10+20+30


def test_session_scoped_to_current_session_id():
    # Old session (S1) near 100%, new session (S2) just started.
    # S2 was started more recently (newer first-event) so it wins.
    events = [
        make_event(NOW - timedelta(hours=3), session="s_old", input_tokens=2_700_000),
        make_event(NOW - timedelta(minutes=30), session="s_new", input_tokens=500_000),
    ]
    snap = aggregate(events, now=NOW, window_limit_tokens=2_766_000, tz=UTC)
    assert snap.session.window_tokens == 500_000
    assert snap.session.window_pct == round(500_000 / 2_766_000 * 100, 1)


def test_session_resets_at_anchored_to_session_start():
    # Reset time = session_start + 5h, regardless of where events are in the window.
    # This matches Claude.ai's "resets in X" which shows when the session's allocation
    # window expires, not when the oldest individual token expires.
    events = [
        make_event(NOW - timedelta(hours=1, minutes=6), session="s1", input_tokens=500_000),
        make_event(NOW - timedelta(minutes=30), session="s1", input_tokens=300_000),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    expected = (NOW - timedelta(hours=1, minutes=6)) + timedelta(hours=5)
    assert snap.session.window_resets_at == expected


def test_session_synthetic_events_counted_normally():
    # <synthetic> model appears constantly during Claude Code tool-use; it is NOT
    # a rate-limit signal and should be counted like any other event.
    events = [
        make_event(NOW - timedelta(hours=1), session="s1",
                   model="<synthetic>", input_tokens=50_000),
        make_event(NOW - timedelta(minutes=30), session="s1",
                   model="claude-sonnet-4-6", input_tokens=300_000),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.session.window_tokens == 350_000
    # session started 1h ago → resets in 4h
    assert snap.session.window_resets_at == (NOW - timedelta(hours=1)) + timedelta(hours=5)


def test_session_picks_newest_start_not_most_recently_active():
    # S_old was started first (4h ago) and has a stray background event 5s ago.
    # S_new was started more recently (30min ago).
    # The stray event should NOT make s_old "win" — we select by session-start time.
    events = [
        make_event(NOW - timedelta(hours=4), session="s_old", input_tokens=500_000),
        make_event(NOW - timedelta(minutes=30), session="s_new", input_tokens=300_000),
        make_event(NOW - timedelta(seconds=5), session="s_old", input_tokens=1_000),  # stray
    ]
    snap = aggregate(events, now=NOW, window_limit_tokens=2_766_000, tz=UTC)
    assert snap.session.window_tokens == 300_000  # s_new, not s_old


def test_session_pct_zero_when_limit_not_configured():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=1_000_000)]
    snap = aggregate(events, now=NOW, tz=UTC, window_limit_tokens=0)
    assert snap.session.window_pct == 0.0


def test_window_resets_at_is_oldest_in_window_plus_5h():
    oldest = NOW - timedelta(hours=3)
    events = [
        make_event(oldest, input_tokens=100),
        make_event(NOW - timedelta(minutes=10), input_tokens=200),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.session.window_resets_at == oldest + timedelta(hours=5)


# NOW = Thursday 2026-05-14 12:00 UTC, default week resets Friday midnight UTC.
# Most recent Friday midnight UTC = 2026-05-08 00:00 UTC.
# Next Friday midnight UTC = 2026-05-15 00:00 UTC.

def test_week_counts_events_since_last_reset():
    events = [
        make_event(NOW - timedelta(days=6, hours=2), input_tokens=100),
        make_event(NOW - timedelta(days=2, hours=1), input_tokens=200),
        make_event(NOW - timedelta(hours=1), input_tokens=300),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.total_tokens == 600


def test_week_drops_events_before_last_reset():
    events = [
        make_event(NOW - timedelta(days=8), input_tokens=9999),  # before May 8 reset
        make_event(NOW - timedelta(hours=1), input_tokens=100),
    ]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.total_tokens == 100


def test_week_excludes_cache_reads_from_total():
    events = [make_event(
        NOW - timedelta(hours=1),
        input_tokens=100,
        output_tokens=200,
        cache_creation_tokens=300,
        cache_read_tokens=5_000_000,  # large but excluded
    )]
    snap = aggregate(events, now=NOW, tz=UTC)
    assert snap.week.total_tokens == 600
    assert snap.week.cache_read_tokens == 5_000_000


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


def test_week_resets_at_is_next_friday_midnight_utc():
    snap = aggregate([], now=NOW, tz=UTC)
    expected = datetime(2026, 5, 15, 0, 0, tzinfo=UTC)
    assert snap.week.resets_at == expected


def test_week_window_pct_against_configured_limit():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=1_400_000)]
    snap = aggregate(events, now=NOW, tz=UTC, week_limit_tokens=10_000_000)
    assert snap.week.window_pct == 14.0


def test_week_window_pct_zero_when_limit_not_configured():
    events = [make_event(NOW - timedelta(hours=1), input_tokens=1_000_000)]
    snap = aggregate(events, now=NOW, tz=UTC, week_limit_tokens=0)
    assert snap.week.window_pct == 0.0


def test_week_respects_custom_reset_hour_and_tz():
    from zoneinfo import ZoneInfo
    dublin = ZoneInfo("Europe/Dublin")
    snap = aggregate([], now=NOW, tz=UTC, week_reset_weekday=4, week_reset_hour=9, week_reset_tz=dublin)
    expected = datetime(2026, 5, 15, 8, 0, tzinfo=UTC)
    assert snap.week.resets_at == expected


def test_week_reset_on_friday_before_reset_hour_stays_in_previous_week():
    from zoneinfo import ZoneInfo
    dublin = ZoneInfo("Europe/Dublin")
    before_reset = datetime(2026, 5, 15, 7, 30, tzinfo=UTC)
    snap = aggregate([], now=before_reset, tz=UTC, week_reset_weekday=4, week_reset_hour=9, week_reset_tz=dublin)
    expected = datetime(2026, 5, 15, 8, 0, tzinfo=UTC)
    assert snap.week.resets_at == expected
