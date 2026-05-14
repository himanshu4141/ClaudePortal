import displayio

HERO_PATH = "/sprites/mascot_hero.bmp"
CORNER_PATH = "/sprites/mascot_corner.bmp"
HERO_WIDTH = 18
HERO_HEIGHT = 13
CORNER_WIDTH = 9
CORNER_HEIGHT = 7

# Hero frame indices (order matches build_sprites.py HERO_FRAMES)
HERO_IDLE = 0
HERO_BLINK = 1
HERO_TYPING = 2
HERO_HAPPY = 3
HERO_THINK = 4
HERO_LOVE = 5
HERO_SWEAT = 6

# Corner frame indices (order matches build_sprites.py CORNER_FRAMES)
CORNER_IDLE = 0
CORNER_BLINK = 1
CORNER_LOOK_L = 2
CORNER_LOOK_R = 3

_hero_bitmap = None
_corner_bitmap = None


def hero_bitmap():
    global _hero_bitmap
    if _hero_bitmap is None:
        _hero_bitmap = displayio.OnDiskBitmap(HERO_PATH)
    return _hero_bitmap


def corner_bitmap():
    global _corner_bitmap
    if _corner_bitmap is None:
        _corner_bitmap = displayio.OnDiskBitmap(CORNER_PATH)
    return _corner_bitmap


def make_hero(x=0, y=0, frame=HERO_IDLE):
    bmp = hero_bitmap()
    tile = displayio.TileGrid(
        bmp,
        pixel_shader=bmp.pixel_shader,
        width=1,
        height=1,
        tile_width=HERO_WIDTH,
        tile_height=HERO_HEIGHT,
        x=x,
        y=y,
    )
    tile[0] = frame
    return tile


def make_corner(x=0, y=0, frame=CORNER_IDLE):
    bmp = corner_bitmap()
    tile = displayio.TileGrid(
        bmp,
        pixel_shader=bmp.pixel_shader,
        width=1,
        height=1,
        tile_width=CORNER_WIDTH,
        tile_height=CORNER_HEIGHT,
        x=x,
        y=y,
    )
    tile[0] = frame
    return tile
