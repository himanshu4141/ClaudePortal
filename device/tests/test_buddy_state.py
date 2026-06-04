import buddy_state as bs
import snapshot_schema as ss


def _state():
    # Fixed clock; every call passes an explicit `now`, so the clock is unused.
    return bs.BuddyState(clock=lambda: 0.0, level_tokens=250_000)


def test_boot_is_sleep_until_first_snapshot():
    s = _state()
    assert s.state(now=0.0) == "sleep"


def test_base_states_from_samples():
    # Fresh state per sample so the first snapshot only sets the level baseline
    # (switching between samples in one state can legitimately cross a level-up).
    for sample, expected in [
        ("idle", "idle"),
        ("busy", "busy"),
        ("thinking", "busy"),     # active but rate==0 still maps to busy poses
        ("attention", "attention"),
    ]:
        s = _state()
        s.update_snapshot(ss.SAMPLES[sample], now=100.0)
        assert s.state(now=100.0) == expected, sample


def test_stale_snapshot_sleeps():
    s = _state()
    s.update_snapshot(ss.SAMPLES["busy"], now=100.0)
    assert s.state(now=100.0) == "busy"
    # Past the staleness window with no new snapshot -> sleep.
    assert s.state(now=100.0 + bs.STALE_SECONDS + 1) == "sleep"


def test_level_up_triggers_celebrate_then_reverts():
    s = _state()
    # First snapshot only sets the level baseline (no boot celebration).
    s.update_snapshot(ss.SAMPLES["busy"], now=10.0)        # week.total 1.51M -> level 6
    assert s.state(now=10.0) == "busy"
    s.update_snapshot(ss.SAMPLES["levelup"], now=11.0)     # week.total 3.01M -> level 12
    assert s.state(now=11.0) == "celebrate"
    # Override expires after CELEBRATE_SECONDS.
    assert s.state(now=11.0 + bs.CELEBRATE_SECONDS + 0.1) == "busy"


def test_no_celebrate_on_first_snapshot():
    s = _state()
    s.update_snapshot(ss.SAMPLES["levelup"], now=5.0)
    assert s.state(now=5.0) != "celebrate"
    assert s.level == 12


def test_shake_triggers_dizzy():
    s = _state()
    s.update_snapshot(ss.SAMPLES["idle"], now=20.0)
    s.on_shake(now=20.5)
    assert s.state(now=21.0) == "dizzy"
    assert s.state(now=20.5 + bs.DIZZY_SECONDS + 0.1) == "idle"


def test_face_down_naps_then_heart_on_wake():
    s = _state()
    s.update_snapshot(ss.SAMPLES["idle"], now=30.0)
    s.set_orientation(True, now=30.0)
    assert s.state(now=31.0) == "nap"
    s.set_orientation(False, now=40.0)        # wake
    assert s.state(now=40.0) == "heart"
    assert s.state(now=40.0 + bs.HEART_SECONDS + 0.1) == "idle"


def test_energy_drains_when_busy_and_refills_in_nap():
    s = _state()
    s.update_snapshot(ss.SAMPLES["busy"], now=0.0)
    s.tick(now=0.0)
    start = s.energy
    s.tick(now=20.0)                          # 20s of busy work
    drained = s.energy
    assert drained < start
    s.set_orientation(True, now=20.0)
    s.tick(now=40.0)                          # 20s face-down nap
    assert s.energy > drained


def test_nap_overrides_everything():
    s = _state()
    s.update_snapshot(ss.SAMPLES["attention"], now=0.0)
    s.on_shake(now=0.0)
    s.set_orientation(True, now=0.0)
    assert s.state(now=0.1) == "nap"
