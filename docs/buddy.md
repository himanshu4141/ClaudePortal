# Desk-pet buddy

Port of [claude-desktop-buddy](https://github.com/anthropics/claude-desktop-buddy)
onto the Matrix Portal M4 LED panel. The upstream project is a bidirectional BLE
companion (it can approve/deny Claude's permission prompts). We keep its *soul* —
the animated pet, the state vocabulary, gamification, and the shake interaction —
but **not** the back-channel: ClaudePortal is a one-way ambient dashboard, so there
is no approve/deny and no transcript. See the top-level `README.md` for the agent →
MQTT → panel data flow.

## Architecture (device-side only)

```
MQTT snapshot ─▶ BuddyController.update_snapshot ─▶ BuddyState (logic)
inputs.poll() ─▶ BuddyController.tick ───────────┘     │ resolves state + gamification
                                                       ▼
                                          BuddyScreen.render ─▶ BuddyEngine
                                                                 │ beat-seq a pose
                                                                 ▼ blit via glyphs
                                                              64×32 LED panel
```

| Module | Role |
|---|---|
| `snapshot_schema.py` | **Pinned** wire contract (`now`/`session`/`week`) + accessors + canned `SAMPLES`. The single place to edit when the agent's payload drifts. |
| `buddy_state.py` | Pure-Python state machine + gamification (level, energy). No `displayio`/`board`, so it's host-unit-testable. |
| `buddy.py` | `BuddyEngine`: owns the 64×32 bitmap; beat-sequences the active pet's poses, centers + blits them, overlays particle effects, draws the bottom status bars. |
| `glyphs.py` | 4×6 pixel font + ASCII-frame blitter. No font file/library on disk. |
| `pets/<name>.py` | Auto-generated pet data: `NAME`, `BODY` (color), `STATES{div, seq, poses}`. One pet resident at a time (RAM is scarce). |
| `pets/__init__.py` | Registry + lazy loader. UP/DOWN cycles `REGISTRY`; selection persists in `microcontroller.nvm`. |
| `inputs.py` | LIS3DH (shake / face-down) + UP/DOWN buttons. Degrades gracefully if a sensor is absent. |
| `buddy_controller.py` | Glue: poll inputs → feed `BuddyState` → render `BuddyScreen`. Replaces the old `moods.py`. |

## State machine

Derived entirely from the snapshot + physical events. Precedence (highest first):

```
nap (face-down)  >  dizzy/heart/celebrate (timed overrides)  >  sleep (stale)  >  base
base ∈ { attention (session ≥ 85%), busy (active), idle }
```

Two upstream states are repurposed since they needed the back-channel: **attention**
(was "approval pending") → session limit warning; **heart** (was "approved in <5 s")
→ wake-from-nap greeting. Tunables (level size, thresholds, durations, energy rates)
live at the top of `buddy_state.py`.

## Porting pets

The 18 upstream species are C++ (`src/buddies/<name>.cpp`): per state, a set of named
5×12 ASCII poses, a `P[]` ordering, a `SEQ[]` beat list, and a `(t / DIV)` divisor.
`tools/port_buddies.py` parses that regular structure and emits a tiny pure-data
Python module per pet (it does **not** port each species' bespoke particle-overlay
code — `buddy.py` renders generic per-state effects instead).

```bash
# vendored sources live in tools/buddy_src/ (download with curl from the upstream repo)
python3 tools/port_buddies.py                 # regenerate all device/pets/*.py
python3 tools/port_buddies.py cat duck        # just these
```

We ship a **curated 6** (`cat, duck, robot, ghost, axolotl, capybara`) to keep flash
and RAM modest — the panel's disk is tight. Add more by downloading the source,
running the tool, and appending the name to `REGISTRY` in `pets/__init__.py`.

> Pose art is variable width (11–15 cols). The 64-px panel fits up to 16 cols at
> 4 px each; `BuddyEngine` centers each pose and clips anything wider.

## Testing

```bash
python3 -m pytest device/tests -q          # font, pet data, state machine, gamification
ADAFRUIT_IO_USERNAME=… ADAFRUIT_IO_KEY=… python3 tools/mock_publish.py   # drive a real panel
```
`mock_publish.py [sample]` cycles (or pins) the `SAMPLES` in `snapshot_schema.py`, so
you can watch idle/busy/attention/celebrate without burning real Claude usage.
