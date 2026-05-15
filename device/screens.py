import displayio
import terminalio
from adafruit_display_text import label

from formatting import (
    PALETTE,
    bar_color_for_pct,
    format_duration,
    format_tokens,
    short_model,
)

WIDTH = 64
HEIGHT = 32


def make_waiting_screen():
    group = displayio.Group()
    group.append(label.Label(terminalio.FONT, text="claude", color=PALETTE["copper"], x=18, y=10))
    group.append(label.Label(terminalio.FONT, text="portal", color=PALETTE["amber"], x=18, y=21))
    return group


def make_now_screen(snapshot):
    group = displayio.Group()
    now = (snapshot or {}).get("now") or {}
    active = now.get("active", False)
    model = short_model(now.get("model"))
    tokens = now.get("tokens") or 0
    duration_min = now.get("duration_min") or 0

    title_color = PALETTE["amber"] if active else PALETTE["cream"]
    group.append(label.Label(terminalio.FONT, text=model, color=title_color, x=2, y=4))
    group.append(
        label.Label(terminalio.FONT, text=format_tokens(tokens), color=PALETTE["copper"], x=2, y=16)
    )
    sub_text = format_duration(duration_min)
    if active:
        sub_text = "* " + sub_text if sub_text else "*"
    group.append(label.Label(terminalio.FONT, text=sub_text, color=PALETTE["cream"], x=2, y=27))
    return group


def make_today_screen(snapshot):
    group = displayio.Group()
    today = (snapshot or {}).get("today") or {}
    tokens = today.get("tokens") or 0
    cost = today.get("cost") or 0
    pct = today.get("window_pct") or 0

    group.append(label.Label(terminalio.FONT, text="TODAY", color=PALETTE["cream"], x=2, y=4))
    group.append(
        label.Label(terminalio.FONT, text=format_tokens(tokens), color=PALETTE["copper"], x=2, y=16)
    )
    cost_text = "${:.2f}".format(cost) if cost else "$0"
    group.append(
        label.Label(terminalio.FONT, text=cost_text, color=PALETTE["pink"], x=40, y=16)
    )

    group.append(_progress_bar(pct, x=2, y=22, width=46, height=4))
    group.append(
        label.Label(
            terminalio.FONT,
            text="{:.0f}%".format(pct),
            color=PALETTE["white"],
            x=50,
            y=25,
        )
    )
    return group


def make_week_screen(snapshot):
    group = displayio.Group()
    week = (snapshot or {}).get("week") or {}
    total = week.get("total") or 0
    days = week.get("days") or [0] * 7
    opus_pct = week.get("opus_pct") or 0
    sonnet_pct = week.get("sonnet_pct") or 0

    group.append(label.Label(terminalio.FONT, text="WK", color=PALETTE["cream"], x=2, y=4))
    group.append(
        label.Label(terminalio.FONT, text=format_tokens(total), color=PALETTE["copper"], x=18, y=4)
    )

    spark = _sparkline(days, x=2, y=10, width=WIDTH - 4, height=10)
    for tile in spark:
        group.append(tile)

    stack = _stacked_bar(opus_pct, sonnet_pct, x=2, y=22, width=WIDTH - 4, height=3)
    for tile in stack:
        group.append(tile)

    label_text = "O{:.0f} S{:.0f}".format(opus_pct, sonnet_pct)
    group.append(label.Label(terminalio.FONT, text=label_text, color=PALETTE["cream"], x=2, y=29))
    return group


def _progress_bar(pct, x, y, width, height):
    pct = max(0, min(100, pct))
    fill_w = int(width * pct / 100)
    bar = displayio.Group(x=x, y=y)
    bar.append(_solid_rect(width, height, PALETTE["dim"]))
    if fill_w > 0:
        fill = _solid_rect(fill_w, height, bar_color_for_pct(pct))
        bar.append(fill)
    return bar


def _sparkline(days, x, y, width, height):
    n = max(1, len(days))
    bar_w = max(1, (width - (n - 1)) // n)
    step = bar_w + 1
    max_val = max(days) if any(d > 0 for d in days) else 1
    tiles = []
    for i, val in enumerate(days):
        h = max(1, int(height * val / max_val)) if val > 0 else 1
        color = PALETTE["amber"] if val > 0 else PALETTE["dim"]
        rect = _solid_rect(bar_w, h, color)
        rect.x = x + i * step
        rect.y = y + height - h
        tiles.append(rect)
    return tiles


def _stacked_bar(opus_pct, sonnet_pct, x, y, width, height):
    total = (opus_pct or 0) + (sonnet_pct or 0)
    if total <= 0:
        return [_place(_solid_rect(width, height, PALETTE["dim"]), x, y)]
    opus_w = int(width * opus_pct / total)
    sonnet_w = width - opus_w
    tiles = []
    if opus_w > 0:
        tiles.append(_place(_solid_rect(opus_w, height, PALETTE["copper"]), x, y))
    if sonnet_w > 0:
        tiles.append(_place(_solid_rect(sonnet_w, height, PALETTE["amber"]), x + opus_w, y))
    return tiles


def _solid_rect(width, height, color):
    bitmap = displayio.Bitmap(max(1, width), max(1, height), 1)
    palette = displayio.Palette(1)
    palette[0] = color
    return displayio.TileGrid(bitmap, pixel_shader=palette)


def _place(tile_grid, x, y):
    tile_grid.x = x
    tile_grid.y = y
    return tile_grid
