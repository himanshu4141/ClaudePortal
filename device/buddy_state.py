"""Buddy state machine + gamification.

Derives the pet's animation state entirely device-side from the pinned snapshot
contract (snapshot_schema) plus physical events (shake, face-down) — no
back-channel. Pure Python: no displayio/board imports, so it runs under pytest on
a host. The renderer (buddy.py) consumes `.state()`, `.level`, `.energy`.

State precedence (highest first):
    nap  >  dizzy/heart/celebrate (timed overrides)  >  sleep(stale)  >  base
where base in {attention, busy, idle}.
"""

import time

import snapshot_schema as ss

# Tunables
LEVEL_TOKENS = 250_000          # one level per this many week tokens
ATTENTION_PCT = 85.0            # session window % that flips to the limit warning
STALE_SECONDS = 90              # no snapshot within this -> pet sleeps

CELEBRATE_SECONDS = 5.0
DIZZY_SECONDS = 4.0
HEART_SECONDS = 4.0

ENERGY_MAX = 100.0
ENERGY_DRAIN_PER_SEC = 0.5      # while actively working
ENERGY_IDLE_REFILL_PER_SEC = 0.2
ENERGY_NAP_REFILL_PER_SEC = 2.0  # face-down recharges fast


def _base_state(snap):
    if ss.session_pct(snap) >= ATTENTION_PCT:
        return "attention"
    if ss.now_active(snap):
        return "busy"
    return "idle"


class BuddyState:
    def __init__(self, clock=time.monotonic, level_tokens=LEVEL_TOKENS):
        self._clock = clock
        self._level_tokens = level_tokens
        self.snapshot = None
        self._base = "sleep"
        self._override = None
        self._override_until = 0.0
        self._level = None              # unknown until first snapshot (no boot celebration)
        self._face_down = False
        self._energy = ENERGY_MAX
        self._last_snapshot_at = None
        self._last_tick = self._clock()

    # --- inputs -----------------------------------------------------------

    def update_snapshot(self, snap, now=None):
        now = self._clock() if now is None else now
        self.snapshot = snap
        self._last_snapshot_at = now
        self._base = _base_state(snap)
        level = ss.week_total(snap) // self._level_tokens
        if self._level is None:
            self._level = level
        elif level > self._level:
            self._level = level
            self._set_override("celebrate", CELEBRATE_SECONDS, now)

    def on_shake(self, now=None):
        self._set_override("dizzy", DIZZY_SECONDS, now)

    def set_orientation(self, face_down, now=None):
        now = self._clock() if now is None else now
        if face_down and not self._face_down:
            self._face_down = True
        elif not face_down and self._face_down:
            self._face_down = False
            self._set_override("heart", HEART_SECONDS, now)  # wake greeting

    # --- outputs ----------------------------------------------------------

    def tick(self, now=None):
        """Advance energy and return the resolved state. Call every loop."""
        now = self._clock() if now is None else now
        self._advance_energy(now)
        self._last_tick = now
        return self.state(now)

    def state(self, now=None):
        now = self._clock() if now is None else now
        if self._face_down:
            return "nap"
        if self._override is not None and now < self._override_until:
            return self._override
        if self._is_stale(now):
            return "sleep"
        return self._base

    @property
    def level(self):
        return self._level or 0

    @property
    def energy(self):
        return int(self._energy)

    @property
    def lively(self):
        return ss.now_rate(self.snapshot) > 0

    # --- internals --------------------------------------------------------

    def _set_override(self, name, seconds, now):
        now = self._clock() if now is None else now
        self._override = name
        self._override_until = now + seconds

    def _is_stale(self, now):
        if self._last_snapshot_at is None:
            return True
        return (now - self._last_snapshot_at) > STALE_SECONDS

    def _advance_energy(self, now):
        dt = now - self._last_tick
        if dt <= 0:
            return
        if self._face_down:
            self._energy += ENERGY_NAP_REFILL_PER_SEC * dt
        elif self._base in ("busy", "attention") and ss.now_active(self.snapshot):
            self._energy -= ENERGY_DRAIN_PER_SEC * dt
        else:
            self._energy += ENERGY_IDLE_REFILL_PER_SEC * dt
        if self._energy > ENERGY_MAX:
            self._energy = ENERGY_MAX
        elif self._energy < 0.0:
            self._energy = 0.0
