from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo

from .models import UsageEvent

ACTIVE_THRESHOLD = timedelta(minutes=5)
WINDOW_DURATION = timedelta(hours=5)
RATE_WINDOW = timedelta(minutes=5)
WEEK_DAYS = 7
DEFAULT_WINDOW_LIMIT_TOKENS = 0  # configure via SESSION_LIMIT_TOKENS env var


@dataclass(frozen=True, slots=True)
class NowMetrics:
    active: bool
    model: str | None
    session_id: str | None
    session_tokens: int
    session_started: datetime | None
    session_duration_minutes: int
    tokens_per_minute: float


@dataclass(frozen=True, slots=True)
class SessionMetrics:
    """5-hour rolling window (Anthropic's rate-limit unit)."""
    window_tokens: int               # in+out+cw; cache_read excluded (10× cheaper, not counted)
    window_input_tokens: int
    window_output_tokens: int
    window_cache_creation_tokens: int
    window_cache_read_tokens: int
    window_pct: float                # % of limit used; 0.0 when limit not configured
    window_resets_at: datetime | None


@dataclass(frozen=True, slots=True)
class WeekMetrics:
    total_tokens: int                # in+out+cw (usage_tokens, excl. cache reads)
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    opus_tokens: int
    sonnet_tokens: int
    opus_pct: float
    sonnet_pct: float
    window_pct: float                # % of weekly limit; 0.0 when limit not configured
    resets_at: datetime              # next week reset (UTC)


@dataclass(frozen=True, slots=True)
class Snapshot:
    generated_at: datetime
    now: NowMetrics
    session: SessionMetrics
    week: WeekMetrics


def aggregate(
    events: Iterable[UsageEvent],
    now: datetime | None = None,
    window_limit_tokens: int = DEFAULT_WINDOW_LIMIT_TOKENS,
    tz: tzinfo | None = None,
    week_reset_weekday: int = 4,       # Friday (Mon=0 … Fri=4 … Sun=6)
    week_reset_hour: int = 0,          # hour-of-day in week_reset_tz
    week_reset_tz: tzinfo | None = None,
    week_limit_tokens: int = 0,        # 0 = not configured → window_pct stays 0.0
) -> Snapshot:
    now = now or datetime.now(timezone.utc)
    if tz is None:
        tz = now.astimezone().tzinfo or timezone.utc
    if week_reset_tz is None:
        week_reset_tz = tz
    events_list = sorted(events, key=lambda e: e.timestamp)
    return Snapshot(
        generated_at=now,
        now=_compute_now(events_list, now),
        session=_compute_session(events_list, now, window_limit_tokens),
        week=_compute_week(
            events_list, now,
            week_limit_tokens, week_reset_weekday, week_reset_hour, week_reset_tz,
        ),
    )


def _compute_now(events: list[UsageEvent], now: datetime) -> NowMetrics:
    if not events:
        return NowMetrics(False, None, None, 0, None, 0, 0.0)

    latest = events[-1]
    active = (now - latest.timestamp) <= ACTIVE_THRESHOLD
    session = [e for e in events if e.session_id == latest.session_id]
    started = session[0].timestamp
    duration = max(timedelta(seconds=1), latest.timestamp - started)
    duration_min = max(1, int(duration.total_seconds() // 60))
    session_tokens = sum(e.total_tokens for e in session)

    rate_window_start = now - RATE_WINDOW
    recent_tokens = sum(e.total_tokens for e in session if e.timestamp >= rate_window_start)
    tpm = recent_tokens / (RATE_WINDOW.total_seconds() / 60)

    return NowMetrics(
        active=active,
        model=latest.model,
        session_id=latest.session_id,
        session_tokens=session_tokens,
        session_started=started,
        session_duration_minutes=duration_min,
        tokens_per_minute=round(tpm, 1),
    )


def _compute_session(
    events: list[UsageEvent],
    now: datetime,
    window_limit_tokens: int,
) -> SessionMetrics:
    window_start = now - WINDOW_DURATION

    # Select the currently active session: the one whose most recent REAL-MODEL event
    # is newest. We skip compact_boundary markers (zero-token) and synthetic events
    # (model in angle brackets) — those are tool-processing noise, not user activity.
    current_session_id: str | None = None
    if events:
        ref = next(
            (e for e in reversed(events)
             if not e.is_compact_boundary
             and not (e.model and e.model.startswith("<"))),
            events[-1],
        )
        current_session_id = ref.session_id

    # Find the effective window start. A compact_boundary system event marks when
    # Claude Code compacted the context — Anthropic resets the session rate-limit
    # counter at this point, so we should too.
    effective_start = window_start
    for e in reversed(events):
        if e.session_id == current_session_id and e.is_compact_boundary:
            if e.timestamp > window_start:
                effective_start = e.timestamp
            break  # only the most recent boundary matters

    # Count events in the effective window (compact_boundary markers excluded from sum).
    window_events = [
        e for e in events
        if e.timestamp >= effective_start
        and e.session_id == current_session_id
        and not e.is_compact_boundary
    ]
    w_input  = sum(e.input_tokens            for e in window_events)
    w_output = sum(e.output_tokens           for e in window_events)
    w_cw     = sum(e.cache_creation_tokens   for e in window_events)
    w_cr     = sum(e.cache_read_tokens       for e in window_events)
    # usage_tokens = input+output+cache_creation; cache reads excluded (~10× cheaper,
    # not counted toward Anthropic's session rate limit)
    window_tokens = w_input + w_output + w_cw
    pct = 100.0 * window_tokens / window_limit_tokens if window_limit_tokens else 0.0
    pct = min(pct, 100.0)

    # Reset time: anchor to the session's own start (first-ever event for this
    # session_id), not the oldest event currently in the rolling window.
    # "session_start + 5h" = when this session's Anthropic allocation window expires,
    # which matches Claude.ai's display. "oldest_event_in_window + 5h" degrades to
    # 0min for any session that has been continuously active for a full 5h cycle.
    resets_at = None
    if current_session_id is not None:
        # Anchor reset time to: compact_boundary timestamp if one exists (most accurate),
        # otherwise the session's own first event (matches Claude.ai's "resets in X").
        # Falls back to rolling oldest-event + 5h for sessions older than 5h.
        anchor = effective_start if effective_start > window_start else min(
            (e.timestamp for e in events if e.session_id == current_session_id),
            default=None,
        )
        if anchor is not None:
            candidate = anchor + WINDOW_DURATION
            if candidate > now:
                resets_at = candidate
            elif window_events:
                resets_at = min(e.timestamp for e in window_events) + WINDOW_DURATION

    return SessionMetrics(
        window_tokens=window_tokens,
        window_input_tokens=w_input,
        window_output_tokens=w_output,
        window_cache_creation_tokens=w_cw,
        window_cache_read_tokens=w_cr,
        window_pct=round(pct, 1),
        window_resets_at=resets_at,
    )


def _compute_week(
    events: list[UsageEvent],
    now: datetime,
    week_limit_tokens: int,
    week_reset_weekday: int,
    week_reset_hour: int,
    week_reset_tz: tzinfo,
) -> WeekMetrics:
    # Find the most recent reset moment at or before now.
    now_in_rtz = now.astimezone(week_reset_tz)
    days_since = (now_in_rtz.weekday() - week_reset_weekday) % 7
    last_reset = now_in_rtz.replace(
        hour=week_reset_hour, minute=0, second=0, microsecond=0
    ) - timedelta(days=days_since)
    if last_reset > now_in_rtz:
        last_reset -= timedelta(days=7)

    week_start_utc = last_reset.astimezone(timezone.utc)
    next_reset_utc = (last_reset + timedelta(days=WEEK_DAYS)).astimezone(timezone.utc)

    w_input = w_output = w_cw = w_cr = 0
    opus = sonnet = 0
    for e in events:
        if e.timestamp < week_start_utc:
            continue
        w_input  += e.input_tokens
        w_output += e.output_tokens
        w_cw     += e.cache_creation_tokens
        w_cr     += e.cache_read_tokens
        family = _model_family(e.model)
        if family == "opus":
            opus += e.usage_tokens
        elif family == "sonnet":
            sonnet += e.usage_tokens

    total = w_input + w_output + w_cw
    coded = opus + sonnet
    opus_pct = round(100.0 * opus / coded, 1) if coded else 0.0
    sonnet_pct = round(100.0 * sonnet / coded, 1) if coded else 0.0
    window_pct = round(100.0 * total / week_limit_tokens, 1) if week_limit_tokens else 0.0
    window_pct = min(window_pct, 100.0)

    return WeekMetrics(
        total_tokens=total,
        input_tokens=w_input,
        output_tokens=w_output,
        cache_creation_tokens=w_cw,
        cache_read_tokens=w_cr,
        opus_tokens=opus,
        sonnet_tokens=sonnet,
        opus_pct=opus_pct,
        sonnet_pct=sonnet_pct,
        window_pct=window_pct,
        resets_at=next_reset_utc,
    )


def _model_family(model: str) -> str | None:
    if not model:
        return None
    if "opus" in model:
        return "opus"
    if "sonnet" in model:
        return "sonnet"
    return None
