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
from mascot import (
    CORNER_HEIGHT,
    CORNER_WIDTH,
    HERO_HEIGHT,
    make_corner,
    make_hero,
)

WIDTH = 64
HEIGHT = 32
CORNER_X = WIDTH - CORNER_WIDTH
HERO_X = 0
HERO_Y = (HEIGHT - HERO_HEIGHT) // 2


class WaitingScreen:
    def __init__(self):
        self.group = displayio.Group()
        self.group.append(label.Label(terminalio.FONT, text="claude", color=PALETTE["copper"], x=18, y=10))
        self.group.append(label.Label(terminalio.FONT, text="portal", color=PALETTE["amber"], x=18, y=21))

    def update_data(self, snapshot):
        return

    def has_hero(self):
        return False

    def has_corner(self):
        return False


class NowScreen:
    def __init__(self):
        self.group = displayio.Group()
        self.hero = make_hero(x=HERO_X, y=HERO_Y)
        text_x = HERO_X + 20
        self.model_label = label.Label(terminalio.FONT, text="", color=PALETTE["cream"], x=text_x, y=5)
        self.tokens_label = label.Label(terminalio.FONT, text="", color=PALETTE["copper"], x=text_x, y=17)
        self.sub_label = label.Label(terminalio.FONT, text="", color=PALETTE["cream"], x=text_x, y=28)
        self.group.append(self.hero)
        self.group.append(self.model_label)
        self.group.append(self.tokens_label)
        self.group.append(self.sub_label)

    def update_data(self, snapshot):
        now = (snapshot or {}).get("now") or {}
        active = now.get("active", False)
        self.model_label.text = short_model(now.get("model"))
        self.model_label.color = PALETTE["amber"] if active else PALETTE["cream"]
        self.tokens_label.text = format_tokens(now.get("tokens") or 0)
        sub = format_duration(now.get("duration_min") or 0)
        if active:
            sub = ("* " + sub) if sub else "*"
        self.sub_label.text = sub

    def has_hero(self):
        return True

    def has_corner(self):
        return False

    def set_hero_frame(self, idx):
        self.hero[0] = idx


class TodayScreen:
    BAR_WIDTH = 46
    BAR_HEIGHT = 4
    BAR_X = 2
    BAR_Y = 22

    def __init__(self):
        self.group = displayio.Group()
        self.corner = make_corner(x=CORNER_X, y=0)
        self.title = label.Label(terminalio.FONT, text="TODAY", color=PALETTE["cream"], x=2, y=4)
        self.tokens_label = label.Label(terminalio.FONT, text="", color=PALETTE["copper"], x=2, y=16)
        self.cost_label = label.Label(terminalio.FONT, text="", color=PALETTE["pink"], x=40, y=16)
        self.pct_label = label.Label(terminalio.FONT, text="", color=PALETTE["white"], x=50, y=25)

        self.bar_bitmap = displayio.Bitmap(self.BAR_WIDTH, self.BAR_HEIGHT, 2)
        self.bar_palette = displayio.Palette(2)
        self.bar_palette[0] = PALETTE["dim"]
        self.bar_palette[1] = PALETTE["amber"]
        self.bar_tile = displayio.TileGrid(
            self.bar_bitmap, pixel_shader=self.bar_palette, x=self.BAR_X, y=self.BAR_Y
        )

        self.group.append(self.title)
        self.group.append(self.corner)
        self.group.append(self.tokens_label)
        self.group.append(self.cost_label)
        self.group.append(self.bar_tile)
        self.group.append(self.pct_label)

    def update_data(self, snapshot):
        today = (snapshot or {}).get("today") or {}
        tokens = today.get("tokens") or 0
        cost = today.get("cost") or 0
        pct = max(0, min(100, today.get("window_pct") or 0))

        self.tokens_label.text = format_tokens(tokens)
        self.cost_label.text = "${:.2f}".format(cost) if cost else "$0"
        self.pct_label.text = "{:.0f}%".format(pct)
        self.bar_palette[1] = bar_color_for_pct(pct)
        self._fill_bar(pct)

    def _fill_bar(self, pct):
        fill_w = int(self.BAR_WIDTH * pct / 100)
        for x in range(self.BAR_WIDTH):
            value = 1 if x < fill_w else 0
            for y in range(self.BAR_HEIGHT):
                self.bar_bitmap[x, y] = value

    def has_hero(self):
        return False

    def has_corner(self):
        return True

    def set_corner_frame(self, idx):
        self.corner[0] = idx


class WeekScreen:
    SPARK_X = 2
    SPARK_Y = 10
    SPARK_WIDTH = WIDTH - 4
    SPARK_HEIGHT = 10
    STACK_X = 2
    STACK_Y = 22
    STACK_WIDTH = WIDTH - 4
    STACK_HEIGHT = 3

    def __init__(self):
        self.group = displayio.Group()
        self.corner = make_corner(x=CORNER_X, y=0)
        self.title = label.Label(terminalio.FONT, text="WK", color=PALETTE["cream"], x=2, y=4)
        self.total_label = label.Label(terminalio.FONT, text="", color=PALETTE["copper"], x=18, y=4)
        self.split_label = label.Label(terminalio.FONT, text="", color=PALETTE["cream"], x=2, y=29)

        self.spark_group = displayio.Group()
        self.stack_group = displayio.Group()

        self.group.append(self.corner)
        self.group.append(self.title)
        self.group.append(self.total_label)
        self.group.append(self.spark_group)
        self.group.append(self.stack_group)
        self.group.append(self.split_label)

    def update_data(self, snapshot):
        week = (snapshot or {}).get("week") or {}
        total = week.get("total") or 0
        days = week.get("days") or [0] * 7
        opus_pct = week.get("opus_pct") or 0
        sonnet_pct = week.get("sonnet_pct") or 0

        self.total_label.text = format_tokens(total)
        self.split_label.text = "O{:.0f} S{:.0f}".format(opus_pct, sonnet_pct)
        self._rebuild_sparkline(days)
        self._rebuild_stacked_bar(opus_pct, sonnet_pct)

    def _rebuild_sparkline(self, days):
        while len(self.spark_group):
            self.spark_group.pop()
        n = max(1, len(days))
        bar_w = max(1, (self.SPARK_WIDTH - (n - 1)) // n)
        step = bar_w + 1
        max_val = max(days) if any(d > 0 for d in days) else 1
        for i, val in enumerate(days):
            h = max(1, int(self.SPARK_HEIGHT * val / max_val)) if val > 0 else 1
            color = PALETTE["amber"] if val > 0 else PALETTE["dim"]
            rect = _solid_rect(bar_w, h, color)
            rect.x = self.SPARK_X + i * step
            rect.y = self.SPARK_Y + self.SPARK_HEIGHT - h
            self.spark_group.append(rect)

    def _rebuild_stacked_bar(self, opus_pct, sonnet_pct):
        while len(self.stack_group):
            self.stack_group.pop()
        total = (opus_pct or 0) + (sonnet_pct or 0)
        if total <= 0:
            bg = _solid_rect(self.STACK_WIDTH, self.STACK_HEIGHT, PALETTE["dim"])
            bg.x = self.STACK_X
            bg.y = self.STACK_Y
            self.stack_group.append(bg)
            return
        opus_w = int(self.STACK_WIDTH * opus_pct / total)
        sonnet_w = self.STACK_WIDTH - opus_w
        if opus_w > 0:
            tile = _solid_rect(opus_w, self.STACK_HEIGHT, PALETTE["copper"])
            tile.x = self.STACK_X
            tile.y = self.STACK_Y
            self.stack_group.append(tile)
        if sonnet_w > 0:
            tile = _solid_rect(sonnet_w, self.STACK_HEIGHT, PALETTE["amber"])
            tile.x = self.STACK_X + opus_w
            tile.y = self.STACK_Y
            self.stack_group.append(tile)

    def has_hero(self):
        return False

    def has_corner(self):
        return True

    def set_corner_frame(self, idx):
        self.corner[0] = idx


def _solid_rect(width, height, color):
    bitmap = displayio.Bitmap(max(1, width), max(1, height), 1)
    palette = displayio.Palette(1)
    palette[0] = color
    return displayio.TileGrid(bitmap, pixel_shader=palette)
