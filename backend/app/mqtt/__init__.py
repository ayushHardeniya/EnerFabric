"""MQTT integration: the transport boundary between simulated/real DER
devices and the backend.

Public surface:

- ``topics`` — deterministic ``enerfabric/telemetry/{asset_id}`` topic
  convention.
- ``codec`` — ``Telemetry`` <-> JSON payload (reuses the domain model,
  no bespoke wire schema).
- ``TelemetryPublisher`` — used by the DER simulator to publish telemetry.
- ``TelemetrySubscriber`` — receives telemetry and hands it to a handler.
- ``service.persist_telemetry`` / ``service.build_telemetry_subscriber`` —
  the one place MQTT is wired to the database (used by ``app.main``'s
  startup/shutdown lifespan).

Deliberately small and replaceable: nothing here depends on the
coordination engine, and nothing in the coordination engine or API routes
depends on this package.
"""

from app.mqtt.publisher import TelemetryPublisher
from app.mqtt.subscriber import TelemetrySubscriber

__all__ = ["TelemetryPublisher", "TelemetrySubscriber"]
