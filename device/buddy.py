"""Pet render/animation engine.

Owns a 64x32 displayio.Bitmap + TileGrid in a Group. Each render: clear, pick the
current pose by beat-sequencing the active pet's data, blit it (horizontally
centered, since upstream poses vary 11-15 cols wide), overlay a small animated
particle effect, then draw two 1px ambient bars on the bottom rows (session
window %, energy).

Animation `t` is derived from the clock so it's frame-rate independent. Mirrors
claude-desktop-buddy's per-species render loop; particle effects are generic
approximations rather than ports of each species' exact overlay code.
"""

import displayio

import glyphs

PANEL_W = 64
PANEL_H = 32
CENTER_X = PANEL_W // 2
PET_H = glyphs.FRAME_ROWS * glyphs.GLYPH_H   # 30; bottom 2 rows are status bars
FRAMES_PER_SEC = 8  # pose-beat clock; upstream divisors assume ~per-frame ticks

# Palette indices (index 0 = transparent background).
BODY, YEL, HEART, CYAN, WHITE, GREEN, DIM = 1, 2, 3, 4, 5, 6, 7
_ACCENTS = {
    YEL: 0xFFD93B,
    HEART: 0xFF5C7A,
    CYAN: 0x4FD0E0,
    WHITE: 0xFFFFFF,
    GREEN: 0x7CD66B,
    DIM: 0x555555,
}

_POSE_STATE = {"nap": "sleep"}  # nap reuses the sleep poses

# Dizzy orbit table (from the upstream effect).
_OX = (0, 5, 7, 5, 0, -5, -7, -5)
_OY = (-5, -3, 0, 3, 5, 3, 0, -3)
_CONFETTI = (YEL, HEART, CYAN, WHITE, GREEN)

_SESSION_Y = PANEL_H - 2   # row 30
_ENERGY_Y = PANEL_H - 1    # row 31


def _clamp_pct(p):
    if p is None or p < 0:
        return 0.0
    return 100.0 if p > 100 else p


class BuddyEngine:
    def __init__(self):
        self.bitmap = displayio.Bitmap(PANEL_W, PANEL_H, 8)
        self.palette = displayio.Palette(8)
        self.palette[0] = 0x000000
        self.palette.make_transparent(0)
        self.palette[BODY] = 0xFFFFFF
        for idx, color in _ACCENTS.items():
            self.palette[idx] = color
        self.tile = displayio.TileGrid(self.bitmap, pixel_shader=self.palette, x=0, y=0)
        self.group = displayio.Group()
        self.group.append(self.tile)
        self._pet = None

    def set_pet(self, pet):
        """Swap the active pet module (exposes NAME, BODY, STATES)."""
        self._pet = pet
        self.palette[BODY] = pet.BODY

    def render(self, state, now):
        if self._pet is None:
            return
        pose_state = _POSE_STATE.get(state, state)
        st = self._pet.STATES.get(pose_state) or self._pet.STATES["idle"]
        t = int(now * FRAMES_PER_SEC)
        seq = st["seq"]
        beat = (t // st["div"]) % len(seq)
        pose = st["poses"][seq[beat]]

        self.bitmap.fill(0)
        cols = max(len(line) for line in pose)
        x0 = (PANEL_W - cols * glyphs.GLYPH_W) // 2
        glyphs.blit_frame(self.bitmap, pose, BODY, x0, 0)
        self._effects(state, t)

    def draw_bars(self, session_pct, energy):
        """Two 1px ambient bars on the bottom rows: session window, energy."""
        sp = _clamp_pct(session_pct)
        sev = HEART if sp >= 85 else (YEL if sp >= 60 else GREEN)
        self._row(_SESSION_Y, int(PANEL_W * sp / 100.0), sev)
        self._row(_ENERGY_Y, int(PANEL_W * _clamp_pct(energy) / 100.0), CYAN)

    def _row(self, y, fill_w, color):
        for x in range(PANEL_W):
            self.bitmap[x, y] = color if x < fill_w else 0

    def _effects(self, state, t):
        b = self.bitmap
        if state in ("sleep", "nap"):
            p = t % 10
            glyphs.blit_glyph(b, "z", DIM, 42, 12 - p)
            glyphs.blit_glyph(b, "Z", WHITE, 48, 10 - p)
        elif state == "attention":
            if (t // 2) & 1:
                glyphs.blit_glyph(b, "!", YEL, CENTER_X - 2, 0)
        elif state == "celebrate":
            for i in range(6):
                y = ((t * 2 + i * 9) % 28)
                x = 4 + i * 11
                if 0 <= y < PET_H and 0 <= x < PANEL_W:
                    b[x, y] = _CONFETTI[i % 5]
        elif state == "dizzy":
            p1, p2 = t % 8, (t + 4) % 8
            glyphs.blit_glyph(b, "*", CYAN, CENTER_X + _OX[p1], 12 + _OY[p1])
            glyphs.blit_glyph(b, "*", YEL, CENTER_X + _OX[p2], 12 + _OY[p2])
        elif state == "heart":
            for i in range(5):
                phase = (t + i * 4) % 16
                glyphs.blit_glyph(b, "v", HEART, CENTER_X - 18 + i * 9, 18 - phase)
