"""Regenerate mascot BMP sprites from the pixel-grid definitions below.

Run with: python3 build_sprites.py

Each grid uses '█' for lit copper pixels and any other character (typically
'.' or '░') for off pixels. Eyes are drawn as off pixels (the LED matrix
background shows through), so the mascot reads correctly without a third
palette colour.
"""
from __future__ import annotations

import struct
from pathlib import Path

HERE = Path(__file__).parent

COPPER = (0xD9, 0x77, 0x57)
OFF = (0x00, 0x00, 0x00)

HERO_IDLE = """
..██████████████..
..██████████████..
..███░██████░███..
..███░██████░███..
..███░██████░███..
..██████████████..
██████████████████
██████████████████
..██████████████..
..██████████████..
....██.██.██.██...
....██.██.██.██...
....██.██.██.██...
"""

CORNER_IDLE = """
.███████.
.███████.
.█░███░█.
█████████
.███████.
.███████.
.█.█.█.█.
"""


def parse_grid(text: str) -> list[list[int]]:
    rows = [row for row in text.split("\n") if row]
    width = max(len(row) for row in rows)
    grid = []
    for row in rows:
        padded = row.ljust(width, ".")
        grid.append([1 if ch == "█" else 0 for ch in padded])
    return grid


def write_bmp_1bpp(path: Path, grid: list[list[int]], fg=COPPER, bg=OFF) -> None:
    h = len(grid)
    w = len(grid[0])
    row_bytes = ((w + 31) // 32) * 4
    pixel_data_size = row_bytes * h
    palette_bytes = 8
    headers_bytes = 14 + 40
    file_size = headers_bytes + palette_bytes + pixel_data_size
    pixel_offset = headers_bytes + palette_bytes

    out = bytearray()
    out += b"BM"
    out += struct.pack("<I", file_size)
    out += struct.pack("<HH", 0, 0)
    out += struct.pack("<I", pixel_offset)

    out += struct.pack("<I", 40)
    out += struct.pack("<i", w)
    out += struct.pack("<i", h)
    out += struct.pack("<HH", 1, 1)
    out += struct.pack("<I", 0)
    out += struct.pack("<I", pixel_data_size)
    out += struct.pack("<ii", 2835, 2835)
    out += struct.pack("<II", 2, 2)

    out += bytes([bg[2], bg[1], bg[0], 0])
    out += bytes([fg[2], fg[1], fg[0], 0])

    for row in reversed(grid):
        bits = 0
        count = 0
        row_bytes_out = bytearray()
        for px in row:
            bits = (bits << 1) | (1 if px else 0)
            count += 1
            if count == 8:
                row_bytes_out.append(bits)
                bits = 0
                count = 0
        if count > 0:
            bits <<= (8 - count)
            row_bytes_out.append(bits)
        while len(row_bytes_out) < row_bytes:
            row_bytes_out.append(0)
        out += row_bytes_out

    path.write_bytes(bytes(out))
    print("wrote {} ({}x{}, {} bytes)".format(path.name, w, h, len(out)))


def main() -> None:
    write_bmp_1bpp(HERE / "mascot_hero.bmp", parse_grid(HERO_IDLE))
    write_bmp_1bpp(HERE / "mascot_corner.bmp", parse_grid(CORNER_IDLE))


if __name__ == "__main__":
    main()
