import json
import time

import board
import busio
import digitalio
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_connection_manager
import adafruit_minimqtt.adafruit_minimqtt as MQTT

from display import ScreenRotator, make_display
from moods import MoodController
from screens import NowScreen, TodayScreen, WaitingScreen, WeekScreen
from secrets import secrets

BROKER = "io.adafruit.com"
PORT = 1883
FEED = "{}/feeds/claude-portal.snapshot".format(secrets["aio_username"])
RETRY_BASE_SECONDS = 5
RETRY_MAX_SECONDS = 60

# Matrix Portal M4: ESP32 co-processor wired to SAMD51 over SPI (AirLift)
_esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
_esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
_esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
_spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
_esp = adafruit_esp32spi.ESP_SPIcontrol(_spi, _esp32_cs, _esp32_ready, _esp32_reset)

display = make_display()
screens = [NowScreen(), TodayScreen(), WeekScreen()]
rotator = ScreenRotator(display, screens, waiting_screen=WaitingScreen())
mood = MoodController(rotator.current_index, screens)


def connect_wifi():
    if _esp.is_connected:
        return
    print("wifi: connecting to {}".format(secrets["ssid"]))
    while not _esp.is_connected:
        try:
            _esp.connect_AP(secrets["ssid"], secrets["password"])
        except OSError as exc:
            print("wifi: error {}".format(exc))
    print("wifi: ip={}".format(_esp.pretty_ip(_esp.ip_address)))


def make_mqtt_client(pool):
    client = MQTT.MQTT(
        broker=BROKER,
        port=PORT,
        username=secrets["aio_username"],
        password=secrets["aio_key"],
        socket_pool=pool,
        keep_alive=30,
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
    mood.update_snapshot(snapshot)


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
    mqtt_client = None
    while True:
        try:
            connect_wifi()
            pool = adafruit_connection_manager.get_radio_socketpool(_esp)
            mqtt_client = make_mqtt_client(pool)
            mqtt_client.connect()
            retry_delay = RETRY_BASE_SECONDS
            while True:
                mqtt_client.loop(timeout=1)
                rotator.tick()
                mood.tick()
        except Exception as exc:  # noqa: BLE001 - top-level guard so the board never wedges
            print("loop: crashed type={} err={}".format(type(exc).__name__, exc))
            print("loop: retrying in {}s".format(retry_delay))
            try:
                if mqtt_client is not None:
                    mqtt_client.disconnect()
            except Exception:
                pass
            try:
                _esp.reset()
            except Exception:
                pass
            time.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, RETRY_MAX_SECONDS)


run()
