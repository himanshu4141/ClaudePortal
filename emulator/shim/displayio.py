"""Minimal displayio shim: Group, Bitmap, Palette, TileGrid, OnDiskBitmap.

Just enough surface area for the ClaudePortal device code. The renderer
walks these objects to composite a 64x32 RGB image.
"""
from __future__ import annotations

import struct
from pathlib import Path


class Group:
    def __init__(self, x: int = 0, y: int = 0):
        self.x = x
        self.y = y
        self.hidden = False
        self._children: list = []

    def append(self, child) -> None:
        self._children.append(child)

    def pop(self, idx: int = -1):
        return self._children.pop(idx)

    def insert(self, idx: int, child) -> None:
        self._children.insert(idx, child)

    def __len__(self) -> int:
        return len(self._children)

    def __iter__(self):
        return iter(self._children)

    def __getitem__(self, idx: int):
        return self._children[idx]


class Bitmap:
    def __init__(self, width: int, height: int, value_count: int):
        self.width = width
        self.height = height
        self.value_count = value_count
        self._data = [0] * (width * height)

    def __setitem__(self, key, value):
        x, y = _xy(key, self.width)
        self._data[y * self.width + x] = value

    def __getitem__(self, key):
        x, y = _xy(key, self.width)
        return self._data[y * self.width + x]


class Palette:
    def __init__(self, n: int):
        self._colors = [0] * n
        self._transparent = [False] * n

    def __setitem__(self, idx: int, color: int):
        self._colors[idx] = color

    def __getitem__(self, idx: int) -> int:
        return self._colors[idx]

    def __len__(self) -> int:
        return len(self._colors)

    def make_transparent(self, idx: int) -> None:
        self._transparent[idx] = True

    def is_transparent(self, idx: int) -> bool:
        return self._transparent[idx]


class TileGrid:
    def __init__(
        self,
        bitmap,
        pixel_shader=None,
        x: int = 0,
        y: int = 0,
        width: int = 1,
        height: int = 1,
        tile_width: int | None = None,
        tile_height: int | None = None,
        default_tile: int = 0,
    ):
        self.bitmap = bitmap
        self.pixel_shader = pixel_shader
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.tile_width = tile_width if tile_width is not None else bitmap.width
        self.tile_height = tile_height if tile_height is not None else bitmap.height
        self.hidden = False
        self._tiles = [default_tile] * (width * height)

    def __setitem__(self, key, value):
        x, y = _xy(key, self.width)
        self._tiles[y * self.width + x] = value

    def __getitem__(self, key) -> int:
        x, y = _xy(key, self.width)
        return self._tiles[y * self.width + x]


class OnDiskBitmap:
    """Load a BMP file as a Bitmap + Palette, mirroring the device API.

    Only handles the 1-bpp BMP format produced by device/sprites/build_sprites.py.
    """

    def __init__(self, path: str):
        resolved = _resolve_circuitpy_path(path)
        bitmap, palette = _load_bmp_1bpp(resolved)
        self._bitmap = bitmap
        self.pixel_shader = palette
        self.width = bitmap.width
        self.height = bitmap.height

    def __getitem__(self, key) -> int:
        return self._bitmap[key]


def _xy(key, width: int) -> tuple[int, int]:
    if isinstance(key, tuple):
        return key[0], key[1]
    return key % width, key // width


def _resolve_circuitpy_path(path: str) -> Path:
    """Map a CIRCUITPY-rooted path like '/sprites/foo.bmp' to a real filesystem path.

    The device drops sprites at /sprites/ on CIRCUITPY; in the emulator we keep
    them under device/sprites/ in the repo.
    """
    raw = Path(path)
    if not raw.is_absolute():
        return raw

    here = Path(__file__).resolve().parent.parent  # emulator/
    repo = here.parent
    candidates = [
        repo / "device" / str(raw).lstrip("/"),
        here / "CIRCUITPY" / str(raw).lstrip("/"),
        raw,
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "Could not resolve CIRCUITPY path {}: tried {}".format(path, candidates)
    )


def _load_bmp_1bpp(path: Path) -> tuple[Bitmap, Palette]:
    data = path.read_bytes()
    if data[:2] != b"BM":
        raise ValueError("Not a BMP: {}".format(path))

    pixel_offset = struct.unpack("<I", data[10:14])[0]
    width = struct.unpack("<i", data[18:22])[0]
    height = struct.unpack("<i", data[22:26])[0]
    bpp = struct.unpack("<H", data[28:30])[0]
    colors_used = struct.unpack("<I", data[46:50])[0] or (1 << bpp)

    palette_start = 14 + 40
    palette = Palette(colors_used)
    for i in range(colors_used):
        offset = palette_start + i * 4
        b, g, r = data[offset], data[offset + 1], data[offset + 2]
        palette[i] = (r << 16) | (g << 8) | b

    bottom_up = height > 0
    h = abs(height)
    row_bytes = ((width * bpp + 31) // 32) * 4
    bitmap = Bitmap(width, h, colors_used)
    for y in range(h):
        src_y = h - 1 - y if bottom_up else y
        row_start = pixel_offset + src_y * row_bytes
        for x in range(width):
            if bpp == 1:
                byte = data[row_start + (x // 8)]
                bit = (byte >> (7 - (x % 8))) & 1
                bitmap[x, y] = bit
            else:
                raise NotImplementedError("emulator OnDiskBitmap only supports 1bpp BMPs")
    return bitmap, palette
