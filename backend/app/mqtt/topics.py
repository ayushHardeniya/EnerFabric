"""Deterministic MQTT topic conventions for EnerFabric telemetry.

One topic per asset, under a fixed prefix: ``enerfabric/telemetry/{asset_id}``.
This is the only place either the publisher (simulator) or the subscriber
(backend) construct/parse a topic string, so the convention can change in
one place without touching the pub/sub logic around it.
"""

TELEMETRY_TOPIC_PREFIX = "enerfabric/telemetry"
TELEMETRY_TOPIC_WILDCARD = f"{TELEMETRY_TOPIC_PREFIX}/#"


def telemetry_topic(asset_id: str) -> str:
    return f"{TELEMETRY_TOPIC_PREFIX}/{asset_id}"


def asset_id_from_topic(topic: str) -> str | None:
    """The asset id embedded in a telemetry topic, or ``None`` if ``topic``
    doesn't match the ``enerfabric/telemetry/{asset_id}`` convention.
    """
    prefix = f"{TELEMETRY_TOPIC_PREFIX}/"
    if not topic.startswith(prefix):
        return None
    asset_id = topic[len(prefix) :]
    return asset_id or None
