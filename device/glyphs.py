r"""Tiny 4x6 monospace pixel font + ASCII-frame blitter.

The pets are 5 rows x 12 cols of ASCII (ported from claude-desktop-buddy). At 4x6
px per cell that's 48x30 px - fits the 64x32 panel with margin. Glyphs are packed
edge-to-edge (no inter-cell gap) so strokes like /\_/\ connect, matching how the
art was drawn for a monospace terminal.

Glyphs are authored as readable '#'/'.' grids and compiled to bit-rows once at
import (bit 3 = leftmost pixel). No font file or library on disk.
"""

GLYPH_W = 4
GLYPH_H = 6
FRAME_COLS = 12
FRAME_ROWS = 5
FRAME_W = FRAME_COLS * GLYPH_W   # 48
FRAME_H = FRAME_ROWS * GLYPH_H   # 30

# Only the characters that actually appear across the ported pets.
_GRID = {
    " ": ("....", "....", "....", "....", "....", "...."),
    "!": (".#..", ".#..", ".#..", ".#..", "....", ".#.."),
    '"': ("#.#.", "#.#.", "....", "....", "....", "...."),
    "#": (".#.#", "####", ".#.#", "####", ".#.#", "...."),
    "'": (".#..", ".#..", "....", "....", "....", "...."),
    "(": ("..#.", ".#..", ".#..", ".#..", ".#..", "..#."),
    ")": (".#..", "..#.", "..#.", "..#.", "..#.", ".#.."),
    "*": ("....", "#.#.", ".#..", "#.#.", "....", "...."),
    "-": ("....", "....", "....", "####", "....", "...."),
    ".": ("....", "....", "....", "....", "....", ".#.."),
    "/": ("...#", "..#.", "..#.", ".#..", ".#..", "#..."),
    "0": (".##.", "#..#", "#..#", "#..#", "#..#", ".##."),
    "1": ("..#.", ".##.", "..#.", "..#.", "..#.", ".###"),
    "3": ("###.", "...#", ".##.", "...#", "...#", "###."),
    "<": ("...#", "..#.", ".#..", ".#..", "..#.", "...#"),
    "=": ("....", "####", "....", "####", "....", "...."),
    ">": ("#...", ".#..", "..#.", "..#.", ".#..", "#..."),
    "?": (".##.", "#..#", "..#.", ".#..", "....", ".#.."),
    "@": (".##.", "#..#", "#.##", "#.##", "#...", ".##."),
    "O": (".##.", "#..#", "#..#", "#..#", "#..#", ".##."),
    "P": ("###.", "#..#", "###.", "#...", "#...", "#..."),
    "W": ("#..#", "#..#", "#..#", "#..#", "####", ".##."),
    "X": ("#..#", ".#.#", "..#.", ".#.#", "#..#", "...."),
    "Z": ("####", "...#", "..#.", ".#..", "#...", "####"),
    "[": (".###", ".#..", ".#..", ".#..", ".#..", ".###"),
    "\\": ("#...", ".#..", ".#..", "..#.", "..#.", "...#"),
    "]": ("###.", "..#.", "..#.", "..#.", "..#.", "###."),
    "^": (".#..", "#.#.", "....", "....", "....", "...."),
    "_": ("....", "....", "....", "....", "....", "####"),
    "`": (".#..", "..#.", "....", "....", "....", "...."),
    "n": ("....", "....", "###.", "#..#", "#..#", "#..#"),
    "o": ("....", "....", ".##.", "#..#", "#..#", ".##."),
    "u": ("....", "....", "#..#", "#..#", "#..#", ".###"),
    "v": ("....", "....", "#..#", "#..#", ".##.", ".##."),
    "w": ("....", "....", "#..#", "#..#", "####", ".##."),
    "x": ("....", "....", "#..#", ".##.", ".##.", "#..#"),
    "z": ("....", "....", "####", "..#.", ".#..", "####"),
    "{": ("..##", "..#.", ".#..", ".#..", "..#.", "..##"),
    "|": (".#..", ".#..", ".#..", ".#..", ".#..", ".#.."),
    "}": ("##..", ".#..", "..#.", "..#.", ".#..", "##.."),
    "~": ("....", "....", "#.#.", ".#.#", "....", "...."),
}
_GRID["´"] = _GRID["`"]  # stray acute accent -> backtick


def _compile(grid):
    font = {}
    for ch, rows in grid.items():
        bits = []
        for row in rows:
            v = 0
            for i, px in enumerate(row):
                if px == "#":
                    v |= (8 >> i)
            bits.append(v)
        font[ch] = tuple(bits)
    return font


FONT = _compile(_GRID)
_BLANK = FONT[" "]


def blit_glyph(bitmap, ch, color, x, y):
    """Draw a single glyph at (x, y). Used for animated particle effects."""
    glyph = FONT.get(ch, _BLANK)
    w = bitmap.width
    h = bitmap.height
    for gy in range(GLYPH_H):
        bitrow = glyph[gy]
        if not bitrow:
            continue
        py = y + gy
        if py < 0 or py >= h:
            continue
        for gx in range(GLYPH_W):
            if bitrow & (8 >> gx):
                px = x + gx
                if 0 <= px < w:
                    bitmap[px, py] = color


def blit_frame(bitmap, lines, color, x0=0, y0=0):
    """Draw a pose (5 strings x 12 chars) into `bitmap` at (x0, y0).

    Sets matching pixels to palette index `color`. Out-of-bounds pixels are
    skipped, so x/y shifts near the edges are safe. Caller clears the bitmap.
    """
    w = bitmap.width
    h = bitmap.height
    for r, line in enumerate(lines):
        cy = y0 + r * GLYPH_H
        for c in range(len(line)):
            glyph = FONT.get(line[c], _BLANK)
            cx = x0 + c * GLYPH_W
            for gy in range(GLYPH_H):
                bitrow = glyph[gy]
                if not bitrow:
                    continue
                py = cy + gy
                if py < 0 or py >= h:
                    continue
                for gx in range(GLYPH_W):
                    if bitrow & (8 >> gx):
                        px = cx + gx
                        if 0 <= px < w:
                            bitmap[px, py] = color
