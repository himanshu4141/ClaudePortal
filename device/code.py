import json
import ssl
import time

import socketpool
import wifi
import adafruit_minimqtt.adafruit_minimqtt as MQTT

from display import ScreenRotator, make_display
from screens import (
    make_now_screen,
    make_today_screen,
    make_waiting_screen,
    make_week_screen,
)
from secrets import secrets

BROKER = "io.adafruit.com"
PORT = 8883
FEED = "{}/feeds/claude-portal.snapshot".format(secrets["aio_username"])
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 60

display = make_display()
rotator = ScreenRotator(
    display,
    screen_factories=[make_now_screen, make_today_screen, make_week_screen],
    waiting_factory=make_waiting_screen,
)


def connect_wifi():
    if wifi.radio.connected:
        return
    print("wifi: connecting to {}".format(secrets["ssid"]))
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    print("wifi: ip={}".format(wifi.radio.ipv4_address))


def make_mqtt_client(pool):
    client = MQTT.MQTT(
        broker=BROKER,
        port=PORT,
        username=secrets["aio_username"],
        password=secrets["aio_key"],
        socket_pool=pool,
        ssl_context=ssl.create_default_context(),
    )
    client.on_connect = _on_connect
    client.on_disconnect = _on_disconnect
    client.on_message = _on_message
    return client


def _on_connect(client, _userdata, _flags, rc):
    print("mqtt: connected rc={}".format(rc))
    client.subscribe(FEED)
    print("mqtt: subscribed to {}".format(FEED))


def _on_disconnect(_client, _userdata, rc):
    print("mqtt: disconnected rc={}".format(rc))


def _on_message(_client, topic, message):
    print("mqtt: msg topic={} bytes={}".format(topic, len(message)))
    try:
        snapshot = json.loads(message)
    except (ValueError, TypeError) as exc:
        print("mqtt: json parse failed: {}".format(exc))
        return
    summarize(snapshot)
    rotator.update_snapshot(snapshot)


def summarize(snapshot):
    now = snapshot.get("now") or {}
    today = snapshot.get("today") or {}
    week = snapshot.get("week") or {}
    print("  NOW   active={} model={} tokens={} rate={}/min".format(
        now.get("active"), now.get("model"), now.get("tokens"), now.get("rate"),
    ))
    print("  TODAY tokens={} cost=${} window={}%".format(
        today.get("tokens"), today.get("cost"), today.get("window_pct"),
    ))
    print("  WEEK  total={} opus={}% sonnet={}%".format(
        week.get("total"), week.get("opus_pct"), week.get("sonnet_pct"),
    ))


def run():
    retry_delay = RETRY_BASE_SECONDS
    while True:
        try:
            connect_wifi()
            pool = socketpool.SocketPool(wifi.radio)
            mqtt_client = make_mqtt_client(pool)
            mqtt_client.connect()
            retry_delay = RETRY_BASE_SECONDS
            while True:
                mqtt_client.loop(timeout=0.5)
                rotator.tick()
        except Exception as exc:  # noqa: BLE001 - top-level guard so the board never wedges
            print("loop: crashed type={} err={}".format(type(exc).__name__, exc))
            print("loop: retrying in {}s".format(retry_delay))
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, RETRY_MAX_SECONDS)


run()
