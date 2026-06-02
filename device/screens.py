import displayio
import terminalio
from adafruit_display_text import label

from formatting import PALETTE, bar_color_for_pct, format_countdown
from mascot import (
    CORNER_HEIGHT,
    CORNER_WIDTH,
    HERO_HEIGHT,
    make_corner,
    make_hero,
)

WIDTH = 64
HEIGHT = 32
CORNER_X = WIDTH - CORNER_WIDTH   # 55
HERO_X = 0
HERO_Y = (HEIGHT - HERO_HEIGHT) // 2   # 9
TEXT_X = HERO_X + 20   # text starts right of the hero


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


class _LimitScreen:
    """Shared layout for session and week limit screens.

    Layout (64×32):
      y=4   : title label (SESS / WEEK) + corner mascot top-right
      y=12–15: progress bar (x=TEXT_X to x=62, 4px tall)
      y=14  : % label right-anchored over bar (white)
      y=24  : countdown label (amber)
    """

    BAR_X = TEXT_X
    BAR_WIDTH = WIDTH - TEXT_X - 2   # 42px
    BAR_HEIGHT = 4
    BAR_Y = 12

    def __init__(self, title: str):
        self.group = displayio.Group()

        self.hero = make_hero(x=HERO_X, y=HERO_Y)
        self.corner = make_corner(x=CORNER_X, y=0)

        self.title_label = label.Label(
            terminalio.FONT, text=title, color=PALETTE["cream"], x=TEXT_X, y=4,
        )
        self.bar_bitmap = displayio.Bitmap(self.BAR_WIDTH, self.BAR_HEIGHT, 2)
        self.bar_palette = displayio.Palette(2)
        self.bar_palette[0] = PALETTE["dim"]
        self.bar_palette[1] = PALETTE["amber"]
        self.bar_tile = displayio.TileGrid(
            self.bar_bitmap, pixel_shader=self.bar_palette,
            x=self.BAR_X, y=self.BAR_Y,
        )
        self.pct_label = label.Label(
            terminalio.FONT, text="", color=PALETTE["white"],
            anchor_point=(1.0, 0.5), anchored_position=(62, 14),
        )
        self.reset_label = label.Label(
            terminalio.FONT, text="", color=PALETTE["amber"], x=TEXT_X, y=24,
        )

        self.group.append(self.hero)
        self.group.append(self.corner)
        self.group.append(self.title_label)
        self.group.append(self.bar_tile)
        self.group.append(self.pct_label)
        self.group.append(self.reset_label)

    def _apply(self, pct: float, resets_in_min):
        pct = max(0.0, min(100.0, pct or 0.0))
        self.pct_label.text = "{:.0f}%".format(pct)
        self.bar_palette[1] = bar_color_for_pct(pct)
        self._fill_bar(pct)
        self.reset_label.text = format_countdown(resets_in_min)

    def _fill_bar(self, pct):
        fill_w = int(self.BAR_WIDTH * pct / 100)
        for x in range(self.BAR_WIDTH):
            v = 1 if x < fill_w else 0
            for y in range(self.BAR_HEIGHT):
                self.bar_bitmap[x, y] = v

    def has_hero(self):
        return True

    def has_corner(self):
        return True

    def set_hero_frame(self, idx):
        self.hero[0] = idx

    def set_corner_frame(self, idx):
        self.corner[0] = idx


class SessionScreen(_LimitScreen):
    """5-hour rolling window: % used + countdown to reset."""

    def __init__(self):
        super().__init__("SESS")

    def update_data(self, snapshot):
        sess = (snapshot or {}).get("session") or {}
        self._apply(sess.get("window_pct"), sess.get("resets_in_min"))


class WeekLimitScreen(_LimitScreen):
    """Weekly limit: % used + countdown to next Friday reset."""

    def __init__(self):
        super().__init__("WEEK")

    def update_data(self, snapshot):
        week = (snapshot or {}).get("week") or {}
        self._apply(week.get("window_pct"), week.get("resets_in_min"))
