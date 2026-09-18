"""Wire format for Telemetry over MQTT.

Reuses the existing domain ``Telemetry`` model directly as the payload
schema (JSON) instead of inventing a parallel MQTT-specific shape —
``model_validate_json`` gives us the same field/range validation the REST
API already relies on, and raises ``pydantic.ValidationError`` uniformly
for both malformed JSON and a validly-shaped-but-invalid payload, which is
the one exception type callers (the subscriber) need to guard against.
"""

from app.domain import Telemetry


def encode_telemetry(telemetry: Telemetry) -> bytes:
    return telemetry.model_dump_json().encode("utf-8")


def decode_telemetry(payload: bytes | str) -> Telemetry:
    """Raises ``pydantic.ValidationError`` if ``payload`` is not valid JSON
    or does not match the ``Telemetry`` shape.
    """
    return Telemetry.model_validate_json(payload)
