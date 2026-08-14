"""Unit tests for ``TelemetrySubscriber``'s message-handling logic,
exercised directly against its callback methods (no real broker
connection) — this is the integration boundary the milestone brief asks
to be covered: decode -> validate -> hand off to the persistence
callback, discarding anything malformed without raising.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.domain import OperatingState, Telemetry
from app.mqtt.codec import encode_telemetry
from app.mqtt.subscriber import TelemetrySubscriber
from app.mqtt.topics import telemetry_topic

SAMPLE = Telemetry(
    asset_id="solar-1",
    timestamp=datetime(2026, 8, 13, 12, 0, tzinfo=UTC),
    power_kw=4.2,
    available=True,
    operating_state=OperatingState.ACTIVE,
)


@dataclass
class FakeMessage:
    topic: str
    payload: bytes


@pytest.fixture
def received():
    return []


@pytest.fixture
def subscriber(received):
    return TelemetrySubscriber(
        host="unused", port=0, on_telemetry=lambda t: received.append(t)
    )


def test_valid_message_is_handed_to_handler(subscriber, received) -> None:
    message = FakeMessage(topic=telemetry_topic("solar-1"), payload=encode_telemetry(SAMPLE))
    subscriber._handle_message(None, None, message)
    assert received == [SAMPLE]


def test_malformed_json_is_discarded(subscriber, received) -> None:
    message = FakeMessage(topic=telemetry_topic("solar-1"), payload=b"not json")
    subscriber._handle_message(None, None, message)
    assert received == []


def test_valid_json_wrong_shape_is_discarded(subscriber, received) -> None:
    message = FakeMessage(topic=telemetry_topic("solar-1"), payload=b'{"foo": "bar"}')
    subscriber._handle_message(None, None, message)
    assert received == []


def test_topic_asset_id_mismatch_is_discarded(subscriber, received) -> None:
    message = FakeMessage(topic=telemetry_topic("battery-1"), payload=encode_telemetry(SAMPLE))
    subscriber._handle_message(None, None, message)
    assert received == []


def test_handler_exception_does_not_propagate() -> None:
    def failing_handler(_telemetry: Telemetry) -> None:
        raise RuntimeError("boom")

    subscriber = TelemetrySubscriber(host="unused", port=0, on_telemetry=failing_handler)
    message = FakeMessage(topic=telemetry_topic("solar-1"), payload=encode_telemetry(SAMPLE))
    subscriber._handle_message(None, None, message)  # must not raise


def test_connect_subscribes_to_telemetry_wildcard(subscriber) -> None:
    calls = []

    class FakeClient:
        def subscribe(self, topic, qos):
            calls.append((topic, qos))

    subscriber._handle_connect(FakeClient(), None, None, 0)
    assert calls == [("enerfabric/telemetry/#", 1)]
