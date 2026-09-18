from app.mqtt.topics import (
    TELEMETRY_TOPIC_PREFIX,
    TELEMETRY_TOPIC_WILDCARD,
    asset_id_from_topic,
    telemetry_topic,
)


def test_telemetry_topic_format() -> None:
    assert telemetry_topic("solar-1") == "enerfabric/telemetry/solar-1"


def test_wildcard_matches_prefix() -> None:
    assert TELEMETRY_TOPIC_WILDCARD == f"{TELEMETRY_TOPIC_PREFIX}/#"


def test_asset_id_from_topic_round_trips() -> None:
    assert asset_id_from_topic(telemetry_topic("battery-1")) == "battery-1"


def test_asset_id_from_topic_rejects_non_matching_prefix() -> None:
    assert asset_id_from_topic("some/other/topic") is None


def test_asset_id_from_topic_rejects_bare_prefix() -> None:
    assert asset_id_from_topic(TELEMETRY_TOPIC_PREFIX) is None
    assert asset_id_from_topic(f"{TELEMETRY_TOPIC_PREFIX}/") is None
