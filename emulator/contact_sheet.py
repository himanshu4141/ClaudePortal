#!/usr/bin/env python3
"""Render the device BuddyEngine to PNG contact sheets (headless, no Tk, no PIL).

Drives the real `device/buddy.py` against the shim displayio, so the output is
pixel-identical to the 64x32 LED panel. Unlike run.py (a live single-frame Tk
viewer) this lays many animation frames out in a grid so you can inspect a whole
state/pet at a glance -- handy for catching jitter, clipping, or off-center art.

Writes (next to this file, under out/):
  - sheet_states_<pet>.png : rows = the 7 states, cols = animation frames over time
  - sheet_pets_idle.png    : rows = all pets (idle), cols = frames over time

Usage:  emulator/.venv/bin/python emulator/contact_sheet.py [pet]   # default cat
        (no third-party deps; the venv is optional, plain python3 works too)
"""
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE / "shim"))            # displayio shim wins
sys.path.insert(1, str(REPO / "device"))

import buddy  # noqa: E402
import pets  # noqa: E402

STATES = ("sleep", "idle", "busy", "attention", "celebrate", "dizzy", "heart")
SCALE = 6
GAP = 2
SEP = (40, 40, 52)        # separator between cells
BG = (0, 0, 0)            # LED "off"


def _rgb(v):
    return ((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)


def frame(engine):
    """64x32 list-of-rows of (r,g,b) for the engine's current bitmap."""
    bmp, pal = engine.bitmap, engine.palette
    out = []
    for y in range(buddy.PANEL_H):
        row = []
        for x in range(buddy.PANEL_W):
            idx = bmp[x, y]
            row.append(BG if pal.is_transparent(idx) else _rgb(pal[idx]))
        out.append(row)
    return out


def write_png(path, canvas):
    h = len(canvas)
    w = len(canvas[0])
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            raw += bytes(canvas[y][x])
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, data):
        return struct.pack(">I", len(data)) + typ + data + struct.pack(
            ">I", zlib.crc32(typ + data) & 0xFFFFFFFF
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def sheet(rows, cols, render_cell):
    """rows x cols grid of 64x32 cells (scaled SCALE), separated by GAP px of SEP."""
    cw, ch = buddy.PANEL_W * SCALE, buddy.PANEL_H * SCALE
    W = cols * cw + (cols + 1) * GAP
    H = rows * ch + (rows + 1) * GAP
    canvas = [[SEP] * W for _ in range(H)]
    for r in range(rows):
        for c in range(cols):
            cell = render_cell(r, c)  # 64x32 (r,g,b)
            ox = GAP + c * (cw + GAP)
            oy = GAP + r * (ch + GAP)
            for y in range(buddy.PANEL_H):
                for x in range(buddy.PANEL_W):
                    px = cell[y][x]
                    for sy in range(SCALE):
                        rowbuf = canvas[oy + y * SCALE + sy]
                        base = ox + x * SCALE
                        for sx in range(SCALE):
                            rowbuf[base + sx] = px
    return canvas


def main(argv):
    pet_name = argv[0] if argv else "cat"
    cols = 6
    times = [c * 0.6 for c in range(cols)]
    engine = buddy.BuddyEngine()
    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)

    # States sheet for one pet.
    pet_idx = pets.REGISTRY.index(pet_name) if pet_name in pets.REGISTRY else 0
    engine.set_pet(pets.load(pet_idx))

    def states_cell(r, c):
        state = STATES[r]
        engine.render(state, times[c])
        engine.draw_bars(92 if state == "attention" else 40, 70)
        return frame(engine)

    out1 = out_dir / "sheet_states_{}.png".format(pets.REGISTRY[pet_idx])
    write_png(out1, sheet(len(STATES), cols, states_cell))
    print("rows top->bottom:", ", ".join(STATES))
    print("wrote", out1)

    # All pets, idle.
    def pets_cell(r, c):
        engine.set_pet(pets.load(r))
        engine.render("idle", times[c])
        engine.draw_bars(40, 70)
        return frame(engine)

    out2 = out_dir / "sheet_pets_idle.png"
    write_png(out2, sheet(pets.count(), cols, pets_cell))
    print("rows top->bottom:", ", ".join(pets.REGISTRY))
    print("wrote", out2)


if __name__ == "__main__":
    main(sys.argv[1:])
