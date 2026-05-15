"""Headless smoke test: build all screens from a sample snapshot and render
each one to a PNG. Verifies the shim + renderer pipeline without needing
a Tk display or MQTT broker.

Run from the repo root:
    emulator/.venv/bin/python emulator/tests/smoke.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EMULATOR = HERE.parent
REPO = EMULATOR.parent

sys.path.insert(0, str(EMULATOR / "shim"))
sys.path.insert(0, str(EMULATOR))
sys.path.insert(0, str(REPO / "device"))

import display  # noqa: E402
import moods  # noqa: E402
import screens  # noqa: E402

from renderer import render  # noqa: E402


def main() -> int:
    snapshot_path = EMULATOR / "snapshots" / "active_session.json"
    with snapshot_path.open() as fh:
        snap = json.load(fh)

    matrix_display = display.make_display()
    panels = [
        ("waiting", screens.WaitingScreen()),
        ("now", screens.NowScreen()),
        ("today", screens.TodayScreen()),
        ("week", screens.WeekScreen()),
    ]
    mood = moods.MoodController(lambda: 0, [p for _, p in panels[1:]])

    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)

    for name, panel in panels:
        if hasattr(panel, "update_data"):
            panel.update_data(snap if name != "waiting" else None)
        matrix_display.root_group = panel.group
        img = render(matrix_display.root_group)
        path = out_dir / "{}.png".format(name)
        img.save(path)
        print("rendered {} -> {} ({} non-black pixels)".format(
            name, path, _count_lit(img)
        ))

    mood.update_snapshot(snap)
    mood.tick()
    print("mood controller tick OK after update_snapshot")
    return 0


def _count_lit(img) -> int:
    return sum(1 for px in img.getdata() if px != (0, 0, 0))


if __name__ == "__main__":
    raise SystemExit(main())
