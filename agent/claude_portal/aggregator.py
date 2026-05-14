from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone, tzinfo

from .models import UsageEvent

ACTIVE_THRESHOLD = timedelta(minutes=5)
WINDOW_DURATION = timedelta(hours=5)
RATE_WINDOW = timedelta(minutes=5)
WEEK_DAYS = 7
DEFAULT_WINDOW_LIMIT_TOKENS = 20_000_000

# USD per 1M tokens. Approximate Pro/Max pricing for cost-equivalent display.
PRICING_PER_MILLION = {
    "opus":   {"in": 15.00, "out": 75.00, "cache_w": 18.75, "cache_r": 1.50},
    "sonnet": {"in":  3.00, "out": 15.00, "cache_w":  3.75, "cache_r": 0.30},
}
DEFAULT_PRICING = PRICING_PER_MILLION["sonnet"]


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
class TodayMetrics:
    total_tokens: int
    estimated_cost_usd: float
    window_tokens: int
    window_pct: float
    window_resets_at: datetime | None


@dataclass(frozen=True, slots=True)
class WeekMetrics:
    total_tokens: int
    per_day_tokens: list[int]
    per_day_labels: list[str]
    opus_tokens: int
    sonnet_tokens: int
    opus_pct: float
    sonnet_pct: float


@dataclass(frozen=True, slots=True)
class Snapshot:
    generated_at: datetime
    now: NowMetrics
    today: TodayMetrics
    week: WeekMetrics


def aggregate(
    events: Iterable[UsageEvent],
    now: datetime | None = None,
    window_limit_tokens: int = DEFAULT_WINDOW_LIMIT_TOKENS,
    tz: tzinfo | None = None,
) -> Snapshot:
    now = now or datetime.now(timezone.utc)
    if tz is None:
        tz = now.astimezone().tzinfo or timezone.utc
    events_list = sorted(events, key=lambda e: e.timestamp)
    return Snapshot(
        generated_at=now,
        now=_compute_now(events_list, now),
        today=_compute_today(events_list, now, tz, window_limit_tokens),
        week=_compute_week(events_list, now, tz),
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


def _compute_today(
    events: list[UsageEvent],
    now: datetime,
    tz: tzinfo,
    window_limit_tokens: int,
) -> TodayMetrics:
    today_start = now.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    today_events = [e for e in events if e.timestamp.astimezone(tz) >= today_start]
    total = sum(e.total_tokens for e in today_events)
    cost = sum(_event_cost(e) for e in today_events)

    window_start = now - WINDOW_DURATION
    window_events = [e for e in events if e.timestamp >= window_start]
    window_tokens = sum(e.total_tokens for e in window_events)
    pct = 100.0 * window_tokens / window_limit_tokens if window_limit_tokens else 0.0
    pct = min(pct, 100.0)

    resets_at = None
    if window_events:
        oldest_in_window = min(e.timestamp for e in window_events)
        resets_at = oldest_in_window + WINDOW_DURATION

    return TodayMetrics(
        total_tokens=total,
        estimated_cost_usd=round(cost, 2),
        window_tokens=window_tokens,
        window_pct=round(pct, 1),
        window_resets_at=resets_at,
    )


def _compute_week(events: list[UsageEvent], now: datetime, tz: tzinfo) -> WeekMetrics:
    today_local = now.astimezone(tz).date()
    days = [today_local - timedelta(days=WEEK_DAYS - 1 - i) for i in range(WEEK_DAYS)]
    labels = [d.strftime("%a")[0] for d in days]
    week_start = datetime.combine(days[0], datetime.min.time(), tzinfo=tz)

    per_day = [0] * WEEK_DAYS
    opus = 0
    sonnet = 0
    for e in events:
        local = e.timestamp.astimezone(tz)
        if local < week_start:
            continue
        idx = (local.date() - days[0]).days
        if not 0 <= idx < WEEK_DAYS:
            continue
        per_day[idx] += e.total_tokens
        family = _model_family(e.model)
        if family == "opus":
            opus += e.total_tokens
        elif family == "sonnet":
            sonnet += e.total_tokens

    coded = opus + sonnet
    opus_pct = round(100.0 * opus / coded, 1) if coded else 0.0
    sonnet_pct = round(100.0 * sonnet / coded, 1) if coded else 0.0

    return WeekMetrics(
        total_tokens=sum(per_day),
        per_day_tokens=per_day,
        per_day_labels=labels,
        opus_tokens=opus,
        sonnet_tokens=sonnet,
        opus_pct=opus_pct,
        sonnet_pct=sonnet_pct,
    )


def _event_cost(e: UsageEvent) -> float:
    pricing = _pricing_for_model(e.model)
    return (
        e.input_tokens * pricing["in"]
        + e.output_tokens * pricing["out"]
        + e.cache_creation_tokens * pricing["cache_w"]
        + e.cache_read_tokens * pricing["cache_r"]
    ) / 1_000_000


def _pricing_for_model(model: str) -> dict:
    family = _model_family(model)
    if family:
        return PRICING_PER_MILLION[family]
    return DEFAULT_PRICING


def _model_family(model: str) -> str | None:
    if "opus" in model:
        return "opus"
    if "sonnet" in model:
        return "sonnet"
    return None
