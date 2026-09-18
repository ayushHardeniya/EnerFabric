"""Small, replaceable MQTT subscriber.

Its only job: receive bytes off the broker, decode them into a domain
``Telemetry`` object, and hand it to a caller-supplied handler. It never
persists anything itself (see ``service.py`` for that wiring) and knows
nothing about the coordination engine or the REST API — keeping this
module a thin, independent transport boundary.

Malformed payloads (invalid JSON, a payload that doesn't match the
``Telemetry`` shape, or a payload whose ``asset_id`` doesn't match the
topic it was published on) are logged and discarded; a handler failure
(e.g. persistence error) is also logged and discarded, never raised into
paho-mqtt's network loop. Either case must not crash the subscriber.
"""

import logging
from collections.abc import Callable

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app.domain import Telemetry
from app.mqtt.codec import decode_telemetry
from app.mqtt.topics import TELEMETRY_TOPIC_WILDCARD, asset_id_from_topic

logger = logging.getLogger(__name__)

TelemetryHandler = Callable[[Telemetry], None]


class TelemetrySubscriber:
    def __init__(
        self, host: str, port: int, on_telemetry: TelemetryHandler, client_id: str = ""
    ) -> None:
        self._host = host
        self._port = port
        self._on_telemetry = on_telemetry
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id
        )
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

    def start(self) -> None:
        self._client.connect(self._host, self._port)
        self._client.loop_start()

    def stop(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def _handle_connect(
        self, client: mqtt.Client, _userdata, _flags, _reason_code, _properties=None
    ) -> None:
        client.subscribe(TELEMETRY_TOPIC_WILDCARD, qos=1)

    def _handle_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage) -> None:
        try:
            telemetry = decode_telemetry(message.payload)
        except ValidationError:
            logger.warning("discarding malformed telemetry payload on topic %s", message.topic)
            return

        topic_asset_id = asset_id_from_topic(message.topic)
        if topic_asset_id is not None and telemetry.asset_id != topic_asset_id:
            logger.warning(
                "discarding telemetry: payload asset_id %r does not match topic %r",
                telemetry.asset_id,
                message.topic,
            )
            return

        try:
            self._on_telemetry(telemetry)
        except Exception:
            logger.exception("telemetry handler failed for asset_id %s", telemetry.asset_id)
