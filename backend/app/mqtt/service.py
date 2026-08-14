"""Wires the MQTT subscriber to persistence (and, once persisted, to the
realtime WebSocket layer).

This is the only module that connects MQTT to the database: each received
``Telemetry`` is persisted through the existing ``app.db.repository``
layer, in its own short-lived session (mirroring the per-request session
lifecycle ``get_db`` already gives HTTP requests). The coordination engine
and the REST routers have no MQTT awareness at all.

After a successful persist, the same telemetry is broadcast to any
connected WebSocket clients via ``ConnectionManager.broadcast_threadsafe``
(Milestone 6) — this runs on paho-mqtt's own background thread, not the
asyncio event loop, which is exactly what ``broadcast_threadsafe`` exists
for. Broadcasting is purely a realtime notification of work already done
here; it never gates or affects persistence.
"""

import logging

from app.core.config import get_settings
from app.db import repository as repo
from app.db.errors import NotFoundError
from app.db.session import SessionLocal
from app.domain import Telemetry
from app.mqtt.subscriber import TelemetrySubscriber
from app.realtime import manager, telemetry_updated_event

logger = logging.getLogger(__name__)


def persist_telemetry(telemetry: Telemetry) -> None:
    """Persist one telemetry reading received over MQTT.

    Telemetry for an asset that hasn't been registered yet (e.g. the
    simulator started publishing before the asset was created via the API)
    is discarded rather than raised — matching how the REST endpoint
    already treats an unknown ``asset_id`` (404, not a crash). Nothing is
    broadcast in that case, since nothing was actually persisted.
    """
    db = SessionLocal()
    try:
        persisted = repo.create_telemetry(db, telemetry)
    except NotFoundError:
        logger.warning("discarding telemetry for unknown asset_id %s", telemetry.asset_id)
        return
    finally:
        db.close()
    manager.broadcast_threadsafe(telemetry_updated_event(persisted))


def build_telemetry_subscriber() -> TelemetrySubscriber:
    settings = get_settings()
    return TelemetrySubscriber(
        host=settings.mqtt_broker_host,
        port=settings.mqtt_broker_port,
        on_telemetry=persist_telemetry,
        client_id="enerfabric-backend",
    )
