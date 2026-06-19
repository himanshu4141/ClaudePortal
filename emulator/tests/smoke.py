"""Headless smoke test: drive the buddy firmware wiring from a sample snapshot
and render each screen to a PNG. Verifies the shim + renderer + BuddyController
pipeline without needing a Tk display or MQTT broker.

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
import screens  # noqa: E402
from buddy_controller import BuddyController  # noqa: E402

from renderer import render  # noqa: E402


def main() -> int:
    snapshot_path = EMULATOR / "snapshots" / "active_session.json"
    with snapshot_path.open() as fh:
        snap = json.load(fh)

    matrix_display = display.make_display()
    buddy_screen = screens.BuddyScreen()
    panels = [buddy_screen, screens.WeekLimitScreen()]
    rotator = display.ScreenRotator(matrix_display, panels, waiting_screen=screens.WaitingScreen())
    controller = BuddyController(buddy_screen)

    rotator.update_snapshot(snap)
    controller.update_snapshot(snap)
    # A few ticks so the controller resolves a state and paints the pet bitmap.
    for _ in range(5):
        controller.tick()

    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)

    named = [("buddy", buddy_screen), ("week", panels[1]), ("waiting", rotator.waiting)]
    for name, panel in named:
        matrix_display.root_group = panel.group
        img = render(matrix_display.root_group)
        path = out_dir / "{}.png".format(name)
        img.save(path)
        print("rendered {} -> {} ({} non-black pixels)".format(
            name, path, _count_lit(img)
        ))

    print("buddy state after ticks: {}".format(controller.state.state(0.0)))
    return 0


def _count_lit(img) -> int:
    return sum(1 for px in img.getdata() if px != (0, 0, 0))


if __name__ == "__main__":
    raise SystemExit(main())
