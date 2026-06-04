import glyphs
import pets

STATES = ("sleep", "idle", "busy", "attention", "celebrate", "dizzy", "heart")


class FakeBitmap:
    """Minimal stand-in for displayio.Bitmap for host tests."""

    def __init__(self, w, h):
        self.width = w
        self.height = h
        self.cells = {}

    def __setitem__(self, xy, v):
        x, y = xy
        assert 0 <= x < self.width and 0 <= y < self.height, "out of bounds: %r" % (xy,)
        self.cells[xy] = v

    def lit(self):
        return sum(1 for v in self.cells.values() if v)


def test_registry_loads_every_pet():
    assert pets.count() == 6
    for i in range(pets.count()):
        mod = pets.load(i)
        assert isinstance(mod.NAME, str)
        assert 0 <= mod.BODY <= 0xFFFFFF


def test_every_pet_has_all_states_with_valid_poses():
    for i in range(pets.count()):
        mod = pets.load(i)
        for st in STATES:
            assert st in mod.STATES, "{} missing {}".format(mod.NAME, st)
            data = mod.STATES[st]
            assert data["div"] >= 1
            poses = data["poses"]
            assert poses, "{}.{} has no poses".format(mod.NAME, st)
            for pose in poses:
                assert len(pose) == 5
                for line in pose:
                    # Upstream art is variable width (11-15 cols); must fit 64px / 4px = 16.
                    assert 1 <= len(line) <= 16
            # Every SEQ index must point at a real pose.
            assert data["seq"]
            assert max(data["seq"]) < len(poses)
            assert min(data["seq"]) >= 0


def test_font_covers_every_character_used_by_pets():
    used = set()
    for i in range(pets.count()):
        mod = pets.load(i)
        for data in mod.STATES.values():
            for pose in data["poses"]:
                for line in pose:
                    used.update(line)
    missing = used - set(glyphs.FONT)
    assert not missing, "font missing glyphs: {}".format(sorted(missing))


def test_blit_frame_draws_within_bounds_and_lights_pixels():
    cat = pets.load(0)
    pose = cat.STATES["idle"]["poses"][0]
    b = FakeBitmap(64, 32)
    glyphs.blit_frame(b, pose, color=1, x0=0, y0=0)
    assert b.lit() > 0


def test_blit_frame_clips_negative_and_overflow_offsets():
    cat = pets.load(0)
    pose = cat.STATES["idle"]["poses"][0]
    b = FakeBitmap(64, 32)
    # Far off-screen shifts must not raise (bounds-checked, just clipped away).
    glyphs.blit_frame(b, pose, color=1, x0=-200, y0=-200)
    glyphs.blit_frame(b, pose, color=1, x0=200, y0=200)
    assert b.lit() == 0
