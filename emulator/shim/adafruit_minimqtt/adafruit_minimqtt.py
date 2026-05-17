"""adafruit_minimqtt shim backed by paho-mqtt for the emulator."""
import paho.mqtt.client as paho


class MMQTTException(Exception):
    pass


class MQTT:
    def __init__(
        self,
        broker: str,
        port: int = 1883,
        username: str | None = None,
        password: str | None = None,
        socket_pool=None,
        ssl_context=None,
        client_id: str | None = None,
        keep_alive: int = 60,
        **_ignored,
    ):
        self.broker = broker
        self.port = port
        self.keep_alive = keep_alive
        self._client = paho.Client(
            paho.CallbackAPIVersion.VERSION2,
            client_id=client_id or "",
        )
        if username and password:
            self._client.username_pw_set(username, password)
        if ssl_context is not None or port == 8883:
            self._client.tls_set()

        self._client.on_connect = self._paho_on_connect
        self._client.on_disconnect = self._paho_on_disconnect
        self._client.on_message = self._paho_on_message

        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None

    def _paho_on_connect(self, _client, _userdata, _flags, reason_code, _props=None):
        rc = int(reason_code) if hasattr(reason_code, "__int__") else reason_code
        if self.on_connect:
            self.on_connect(self, None, None, rc)

    def _paho_on_disconnect(self, _client, _userdata, _flags, reason_code, _props=None):
        rc = int(reason_code) if hasattr(reason_code, "__int__") else reason_code
        if self.on_disconnect:
            self.on_disconnect(self, None, rc)

    def _paho_on_message(self, _client, _userdata, msg):
        if self.on_message:
            payload = msg.payload.decode("utf-8", errors="replace")
            self.on_message(self, msg.topic, payload)

    def connect(self) -> None:
        self._client.connect(self.broker, self.port, keepalive=self.keep_alive)

    def disconnect(self) -> None:
        try:
            self._client.disconnect()
        except Exception:
            pass

    def subscribe(self, topic: str, qos: int = 1) -> None:
        self._client.subscribe(topic, qos=qos)

    def publish(self, topic: str, payload: str, qos: int = 1) -> None:
        self._client.publish(topic, payload, qos=qos)

    def loop(self, timeout: float = 1) -> None:
        self._client.loop(timeout=timeout)
