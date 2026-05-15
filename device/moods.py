import random
import time

import mascot

BLINK_DURATION = 0.15
BLINK_INTERVAL_MIN = 3.0
BLINK_INTERVAL_MAX = 6.0
HAPPY_DURATION = 5.0
MILESTONE_TOKEN_THRESHOLDS = (1_000_000, 5_000_000, 10_000_000)


def base_state_for(snapshot):
    if not snapshot:
        return mascot.HERO_IDLE
    now = snapshot.get("now") or {}
    today = snapshot.get("today") or {}
    if (today.get("window_pct") or 0) >= 85:
        return mascot.HERO_SWEAT
    if now.get("active"):
        if (now.get("rate") or 0) > 0:
            return mascot.HERO_TYPING
        return mascot.HERO_THINK
    return mascot.HERO_IDLE


class MoodController:
    def __init__(self, screen_index_getter, screens):
        self._screens = screens
        self._current_screen = screen_index_getter
        self._base_state = mascot.HERO_IDLE
        self._override_state = None
        self._override_until = 0.0
        self._last_milestone_value = 0
        self._blink_until = 0.0
        self._next_blink_at = time.monotonic() + random.uniform(
            BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX
        )

    def update_snapshot(self, snapshot):
        self._base_state = base_state_for(snapshot)
        if snapshot is not None:
            today_tokens = (snapshot.get("today") or {}).get("tokens") or 0
            crossed = _milestone_crossed(self._last_milestone_value, today_tokens)
            self._last_milestone_value = today_tokens
            if crossed:
                self._trigger_happy()

    def tick(self):
        t = time.monotonic()
        if t >= self._next_blink_at and t >= self._blink_until:
            self._blink_until = t + BLINK_DURATION
            self._next_blink_at = (
                t + BLINK_DURATION + random.uniform(BLINK_INTERVAL_MIN, BLINK_INTERVAL_MAX)
            )
        self._render(t)

    def _trigger_happy(self):
        self._override_state = mascot.HERO_HAPPY
        self._override_until = time.monotonic() + HAPPY_DURATION

    def _resolve_hero_frame(self, t):
        if t < self._blink_until:
            return mascot.HERO_BLINK
        if self._override_state is not None and t < self._override_until:
            return self._override_state
        return self._base_state

    def _resolve_corner_frame(self, t, hero_frame):
        if t < self._blink_until:
            return mascot.CORNER_BLINK
        if hero_frame == mascot.HERO_TYPING:
            return mascot.CORNER_LOOK_L
        if hero_frame == mascot.HERO_THINK:
            return mascot.CORNER_LOOK_R
        return mascot.CORNER_IDLE

    def _render(self, t):
        hero_frame = self._resolve_hero_frame(t)
        corner_frame = self._resolve_corner_frame(t, hero_frame)
        idx = self._current_screen()
        for i, screen in enumerate(self._screens):
            if i == idx and screen.has_hero():
                screen.set_hero_frame(hero_frame)
            if i == idx and screen.has_corner():
                screen.set_corner_frame(corner_frame)


def _milestone_crossed(prev, curr):
    for threshold in MILESTONE_TOKEN_THRESHOLDS:
        if prev < threshold <= curr:
            return True
    return False
