from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain import OperatingState, Telemetry
from app.mqtt.codec import decode_telemetry, encode_telemetry

SAMPLE = Telemetry(
    asset_id="solar-1",
    timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
    power_kw=4.2,
    energy_kwh=1.5,
    soc_percent=None,
    available=True,
    operating_state=OperatingState.ACTIVE,
)


def test_encode_produces_bytes() -> None:
    payload = encode_telemetry(SAMPLE)
    assert isinstance(payload, bytes)
    assert b"solar-1" in payload


def test_round_trip_preserves_telemetry() -> None:
    payload = encode_telemetry(SAMPLE)
    decoded = decode_telemetry(payload)
    assert decoded == SAMPLE


def test_decode_rejects_invalid_json() -> None:
    with pytest.raises(ValidationError):
        decode_telemetry(b"not json at all")


def test_decode_rejects_valid_json_wrong_shape() -> None:
    with pytest.raises(ValidationError):
        decode_telemetry(b'{"foo": "bar"}')


def test_decode_rejects_out_of_range_field() -> None:
    payload = SAMPLE.model_copy(update={"soc_percent": 150}).model_dump_json(
        warnings=False
    )
    # soc_percent must be validated on decode even though the in-memory
    # copy above bypassed Telemetry's own constructor validation.
    with pytest.raises(ValidationError):
        decode_telemetry(payload)
