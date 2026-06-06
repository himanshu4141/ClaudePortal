"""Run the ClaudePortal device firmware on the host with a Tk viewer.

Two modes:
  --snapshot path/to/snap.json   render a single static snapshot (no MQTT); the
                                  pet still animates and the screens still rotate
  --mqtt                          subscribe to Adafruit IO and render live
                                  updates (default if --snapshot is omitted)

The device modules under ../device run unchanged. We put the shim package
directory first on sys.path so `import board`, `import displayio`, `import
adafruit_lis3dh`, etc. find the host-side stand-ins instead of failing. The
buddy's BuddyController (shake / face-down / buttons) runs too: the input
shims report a flat, unshaken board, so the pet follows the snapshot state.
Set EMU_SHAKE=1 / EMU_FACE_DOWN=1 to force the dizzy / nap paths.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

# Order matters: shims first, emulator dir (for secrets.py), then device.
sys.path.insert(0, str(HERE / "shim"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "device"))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(HERE / ".env")
load_dotenv(REPO / "agent" / ".env")

import display  # noqa: E402  (from device/display.py via sys.path)
import pets  # noqa: E402
import screens  # noqa: E402
from buddy_controller import BuddyController  # noqa: E402

from renderer import render  # noqa: E402
from viewer import Viewer  # noqa: E402

FEED_TEMPLATE = "{username}/feeds/claude-portal.snapshot"


def _set_pet(controller, name):
    """Point the controller's pet selector at a pet by name (emulator helper)."""
    if name not in pets.REGISTRY:
        print("emulator: unknown pet {!r}; choices: {}".format(
            name, ", ".join(pets.REGISTRY)), file=sys.stderr)
        return
    controller.selector.index = pets.REGISTRY.index(name)
    controller.screen.engine.set_pet(controller.selector.load_module())
    print("buddy: pet -> {}".format(controller.selector.name()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, help="Render a single snapshot JSON and stay there.")
    parser.add_argument("--mqtt", action="store_true", help="Subscribe to Adafruit IO and render live.")
    parser.add_argument("--scale", type=int, default=12, help="Pixel scale factor for the viewer.")
    parser.add_argument("--fps", type=int, default=30, help="Viewer refresh rate.")
    parser.add_argument(
        "--pet", choices=pets.REGISTRY,
        help="Start on this pet (default: cat). Arrow keys cycle pets live.",
    )
    args = parser.parse_args()

    use_mqtt = args.mqtt or args.snapshot is None

    matrix_display = display.make_display()
    buddy_screen = screens.BuddyScreen()
    panels = [buddy_screen, screens.WeekLimitScreen()]
    rotator = display.ScreenRotator(matrix_display, panels, waiting_screen=screens.WaitingScreen())
    controller = BuddyController(buddy_screen)

    if args.pet is not None:
        _set_pet(controller, args.pet)

    if args.snapshot is not None:
        with args.snapshot.open() as fh:
            snap = json.load(fh)
        rotator.update_snapshot(snap)
        controller.update_snapshot(snap)

    if use_mqtt:
        creds = _load_credentials()
        if not creds:
            print(
                "emulator: ADAFRUIT_IO_USERNAME / ADAFRUIT_IO_KEY missing -- "
                "set them in emulator/.env or pass --snapshot for offline mode.",
                file=sys.stderr,
            )
            return 2
        threading.Thread(
            target=_mqtt_thread,
            args=(creds, rotator, controller),
            daemon=True,
        ).start()

    viewer = Viewer(scale=args.scale)
    frame_interval = 1.0 / max(1, args.fps)
    last_render = 0.0

    try:
        while viewer.alive():
            delta = viewer.consume_pet_delta()
            if delta:
                controller.selector.nudge(delta)
                controller.screen.engine.set_pet(controller.selector.load_module())
                print("buddy: pet -> {}".format(controller.selector.name()))
            rotator.tick()
            controller.tick()
            now = time.monotonic()
            if now - last_render >= frame_interval:
                viewer.update_image(render(matrix_display.root_group))
                last_render = now
            viewer.poll()
            time.sleep(0.005)
    except KeyboardInterrupt:
        pass
    return 0


def _load_credentials() -> dict | None:
    username = os.environ.get("ADAFRUIT_IO_USERNAME")
    key = os.environ.get("ADAFRUIT_IO_KEY")
    if not username or not key:
        return None
    return {"username": username, "key": key}


def _mqtt_thread(creds: dict, rotator, controller) -> None:
    import ssl

    import adafruit_minimqtt.adafruit_minimqtt as MQTT
    import socketpool
    import wifi

    pool = socketpool.SocketPool(wifi.radio)
    client = MQTT.MQTT(
        broker="io.adafruit.com",
        port=8883,
        username=creds["username"],
        password=creds["key"],
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
    )
    feed = FEED_TEMPLATE.format(username=creds["username"])

    def _on_connect(_c, _u, _f, rc):
        print("emulator mqtt: connected rc={}".format(rc))
        client.subscribe(feed)

    def _on_message(_c, topic, message):
        print("emulator mqtt: msg topic={} bytes={}".format(topic, len(message)))
        try:
            snap = json.loads(message)
        except (ValueError, TypeError) as exc:
            print("emulator mqtt: parse failed: {}".format(exc))
            return
        rotator.update_snapshot(snap)
        controller.update_snapshot(snap)

    client.on_connect = _on_connect
    client.on_message = _on_message
    client.connect()
    while True:
        try:
            client.loop(timeout=1)
        except Exception as exc:  # noqa: BLE001
            print("emulator mqtt: loop error {}: {}".format(type(exc).__name__, exc))
            time.sleep(2)


if __name__ == "__main__":
    raise SystemExit(main())
