"""Composite a displayio Group tree onto a 64x32 PIL image."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

import displayio
from adafruit_display_text import label

WIDTH = 64
HEIGHT = 32

_FONT: ImageFont.ImageFont | None = None


def _font():
    global _FONT
    if _FONT is None:
        _FONT = ImageFont.load_default()
    return _FONT


def render(root_group) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
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
    # CircuitPython label y is the baseline; PIL draws from the top, so back off
    # a few pixels so the text sits near the same row it would on the panel.
    y_top = oy + lbl.y - 7
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
