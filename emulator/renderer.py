"""Composite a displayio Group tree onto a 64x32 PIL image."""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

import displayio
from adafruit_display_text import label

WIDTH = 64
HEIGHT = 32

# CircuitPython's terminalio.FONT is a 6x12 bitmap font rendered with no
# anti-aliasing. We try common system monospace fonts at a tiny pixel size
# and force binary rasterization to approximate that look.
_FONT_CANDIDATES = [
    "/System/Library/Fonts/Monaco.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Courier New.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "Menlo.ttc",
    "DejaVuSansMono.ttf",
]
_FONT_SIZE = 8

_FONT: ImageFont.ImageFont | None = None
_FONT_LOGGED = False


def _font():
    global _FONT, _FONT_LOGGED
    if _FONT is not None:
        return _FONT
    for path in _FONT_CANDIDATES:
        if "/" in path and not os.path.exists(path):
            continue
        try:
            _FONT = ImageFont.truetype(path, _FONT_SIZE)
            if not _FONT_LOGGED:
                print("emulator: using font {} at {}pt".format(path, _FONT_SIZE))
                _FONT_LOGGED = True
            return _FONT
        except OSError:
            continue
    _FONT = ImageFont.load_default()
    if not _FONT_LOGGED:
        print("emulator: no truetype monospace found, falling back to PIL default (text will look big)")
        _FONT_LOGGED = True
    return _FONT


def render(root_group) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    # mode "1" on the host image disables anti-aliasing in ImageDraw.text so
    # glyphs land on integer pixel boundaries -- much closer to how the LED
    # panel will render them.
    img.fontmode = "1"
    if root_group is None:
        return img
    _draw(root_group, img, 0, 0)
    return img


def _draw(node, img: Image.Image, ox: int, oy: int) -> None:
    if getattr(node, "hidden", False):
        return
    nx = getattr(node, "x", 0)
    ny = getattr(node, "y", 0)

    if isinstance(node, displayio.Group):
        for child in node:
            _draw(child, img, ox + nx, oy + ny)
        return

    if isinstance(node, displayio.TileGrid):
        _draw_tilegrid(node, img, ox, oy)
        return

    if isinstance(node, label.Label):
        _draw_label(node, img, ox, oy)
        return


def _draw_tilegrid(tg, img: Image.Image, ox: int, oy: int) -> None:
    bitmap = tg.bitmap
    palette = tg.pixel_shader
    tiles_per_row = max(1, bitmap.width // tg.tile_width)

    base_x = ox + tg.x
    base_y = oy + tg.y

    for grid_y in range(tg.height):
        for grid_x in range(tg.width):
            tile_idx = tg[grid_x, grid_y]
            src_tile_x = (tile_idx % tiles_per_row) * tg.tile_width
            src_tile_y = (tile_idx // tiles_per_row) * tg.tile_height

            for py in range(tg.tile_height):
                src_y = src_tile_y + py
                if src_y < 0 or src_y >= bitmap.height:
                    continue
                dst_y = base_y + grid_y * tg.tile_height + py
                if dst_y < 0 or dst_y >= HEIGHT:
                    continue
                for px in range(tg.tile_width):
                    src_x = src_tile_x + px
                    if src_x < 0 or src_x >= bitmap.width:
                        continue
                    dst_x = base_x + grid_x * tg.tile_width + px
                    if dst_x < 0 or dst_x >= WIDTH:
                        continue
                    color_idx = bitmap[src_x, src_y]
                    if palette is not None and palette.is_transparent(color_idx):
                        continue
                    rgb = _palette_color(palette, color_idx)
                    img.putpixel((dst_x, dst_y), rgb)


def _draw_label(lbl, img: Image.Image, ox: int, oy: int) -> None:
    text = lbl.text or ""
    if not text:
        return
    color = _to_rgb(lbl.color)
    draw = ImageDraw.Draw(img)
    # adafruit_display_text.Label vertically centers the glyph bbox on lbl.y
    # when anchor_point is None (the default the device code uses). For an
    # 8pt monospace that means glyph top ~ lbl.y - 4.
    y_top = oy + lbl.y - 4
    draw.text((ox + lbl.x, y_top), text, fill=color, font=_font())


def _palette_color(palette, idx: int) -> tuple[int, int, int]:
    if palette is None:
        return (255, 255, 255)
    return _to_rgb(palette[idx])


def _to_rgb(value) -> tuple[int, int, int]:
    if value is None:
        return (0, 0, 0)
    if isinstance(value, tuple):
        return value
    return ((value >> 16) & 0xFF, (value >> 8) & 0xFF, value & 0xFF)
