import displayio

HERO_PATH = "/sprites/mascot_hero.bmp"
CORNER_PATH = "/sprites/mascot_corner.bmp"
HERO_WIDTH = 18
HERO_HEIGHT = 13
CORNER_WIDTH = 9
CORNER_HEIGHT = 7

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


def make_hero(x=0, y=0):
    bmp = hero_bitmap()
    return displayio.TileGrid(bmp, pixel_shader=bmp.pixel_shader, x=x, y=y)


def make_corner(x=0, y=0):
    bmp = corner_bitmap()
    return displayio.TileGrid(bmp, pixel_shader=bmp.pixel_shader, x=x, y=y)
