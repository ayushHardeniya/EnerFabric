"""Small, replaceable MQTT publisher for EnerFabric telemetry.

Used today by the DER simulator (see ``run_simulator.py``) to behave like
external device infrastructure — publishing over MQTT rather than mutating
backend state directly — so a real device adapter can later reuse this
same class unchanged.
"""

import paho.mqtt.client as mqtt

from app.domain import Telemetry
from app.mqtt.codec import encode_telemetry
from app.mqtt.topics import telemetry_topic


class TelemetryPublisher:
    def __init__(self, host: str, port: int, client_id: str = "") -> None:
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=client_id
        )
        self._client.connect(host, port)
        self._client.loop_start()

    def publish(self, telemetry: Telemetry) -> None:
        self._client.publish(
            telemetry_topic(telemetry.asset_id), encode_telemetry(telemetry), qos=1
        )

    def close(self) -> None:
        self._client.loop_stop()
        self._client.disconnect()

    def __enter__(self) -> "TelemetryPublisher":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
