"""Pinned snapshot contract (the seam between the agent and this device).

Frozen against `claude/stabilise-device-cp9`
agent/claude_portal/publisher.py::snapshot_to_payload. The agent may evolve as
metric work merges to main; when it does, update THIS file (and anything that
reads these keys) — it is the single place the device's view of the wire format
lives. Buddy/pet state is derived entirely from these fields, device-side.

Wire shape:
    { "ts": str,
      "now":     { "active": bool, "model": str|null, "rate": float },
      "session": { "window_pct": float, "window_tokens": int,
                   "resets_in_min": int|null, "tok": {in,out,cw,cr} },
      "week":    { "window_pct": float, "resets_in_min": int|null,
                   "total": int, "tok": {in,out,cw,cr} } }
"""

# --- accessors (tolerant of missing keys; safe defaults) -------------------

def now_active(snap):
    return bool(((snap or {}).get("now") or {}).get("active"))


def now_rate(snap):
    return ((snap or {}).get("now") or {}).get("rate") or 0.0


def now_model(snap):
    return ((snap or {}).get("now") or {}).get("model")


def session_pct(snap):
    return ((snap or {}).get("session") or {}).get("window_pct") or 0.0


def session_resets_in_min(snap):
    return ((snap or {}).get("session") or {}).get("resets_in_min")


def week_total(snap):
    return ((snap or {}).get("week") or {}).get("total") or 0


def week_pct(snap):
    return ((snap or {}).get("week") or {}).get("window_pct") or 0.0


def week_resets_in_min(snap):
    return ((snap or {}).get("week") or {}).get("resets_in_min")


# --- canned samples for offline/mock testing (tools/mock_publish.py) -------
# Cover each derivable state so the panel can be exercised without real usage.

SAMPLES = {
    "idle": {
        "ts": "2026-06-04T12:00:00+00:00",
        "now": {"active": False, "model": None, "rate": 0.0},
        "session": {"window_pct": 12.0, "window_tokens": 332_000, "resets_in_min": 210,
                    "tok": {"in": 100_000, "out": 30_000, "cw": 202_000, "cr": 0}},
        "week": {"window_pct": 8.0, "resets_in_min": 4320, "total": 1_250_000,
                 "tok": {"in": 400_000, "out": 150_000, "cw": 700_000, "cr": 0}},
    },
    "busy": {
        "ts": "2026-06-04T12:01:00+00:00",
        "now": {"active": True, "model": "claude-opus-4-8", "rate": 1850.0},
        "session": {"window_pct": 41.0, "window_tokens": 1_134_000, "resets_in_min": 188,
                    "tok": {"in": 300_000, "out": 120_000, "cw": 714_000, "cr": 0}},
        "week": {"window_pct": 19.0, "resets_in_min": 4100, "total": 1_510_000,
                 "tok": {"in": 500_000, "out": 200_000, "cw": 810_000, "cr": 0}},
    },
    "thinking": {  # active but no token flow yet
        "ts": "2026-06-04T12:02:00+00:00",
        "now": {"active": True, "model": "claude-sonnet-4-6", "rate": 0.0},
        "session": {"window_pct": 41.0, "window_tokens": 1_134_000, "resets_in_min": 188,
                    "tok": {"in": 300_000, "out": 120_000, "cw": 714_000, "cr": 0}},
        "week": {"window_pct": 19.0, "resets_in_min": 4100, "total": 1_510_000,
                 "tok": {"in": 500_000, "out": 200_000, "cw": 810_000, "cr": 0}},
    },
    "attention": {  # session window near the limit -> warning
        "ts": "2026-06-04T12:03:00+00:00",
        "now": {"active": True, "model": "claude-opus-4-8", "rate": 2400.0},
        "session": {"window_pct": 92.0, "window_tokens": 2_545_000, "resets_in_min": 26,
                    "tok": {"in": 700_000, "out": 300_000, "cw": 1_545_000, "cr": 0}},
        "week": {"window_pct": 33.0, "resets_in_min": 3800, "total": 1_780_000,
                 "tok": {"in": 600_000, "out": 250_000, "cw": 930_000, "cr": 0}},
    },
    "levelup": {  # week.total jumped a LEVEL_TOKENS boundary -> celebrate
        "ts": "2026-06-04T12:04:00+00:00",
        "now": {"active": True, "model": "claude-opus-4-8", "rate": 900.0},
        "session": {"window_pct": 50.0, "window_tokens": 1_383_000, "resets_in_min": 150,
                    "tok": {"in": 400_000, "out": 150_000, "cw": 833_000, "cr": 0}},
        "week": {"window_pct": 55.0, "resets_in_min": 3000, "total": 3_010_000,
                 "tok": {"in": 1_000_000, "out": 400_000, "cw": 1_610_000, "cr": 0}},
    },
}
