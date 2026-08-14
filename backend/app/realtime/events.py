"""The realtime event envelope broadcast over the WebSocket layer.

Every event is::

    {
      "type": "telemetry.updated" | "coordination.completed",
      "timestamp": "<ISO-8601 UTC>",
      "data": { ... }
    }

``data`` reuses the existing domain models' own JSON shape
(``model_dump(mode="json")``) rather than inventing a bespoke realtime
schema — the same choice Milestone 5 made for the MQTT payload. This
keeps the envelope minimal and gives the frontend one shape per event
type it can already validate against the domain model it displays.
"""

from datetime import UTC, datetime
from typing import Any

from app.domain import CoordinationRun, Telemetry

TELEMETRY_UPDATED = "telemetry.updated"
COORDINATION_COMPLETED = "coordination.completed"


def _envelope(event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": data,
    }


def telemetry_updated_event(telemetry: Telemetry) -> dict[str, Any]:
    return _envelope(TELEMETRY_UPDATED, telemetry.model_dump(mode="json"))


def coordination_completed_event(run: CoordinationRun) -> dict[str, Any]:
    return _envelope(COORDINATION_COMPLETED, run.model_dump(mode="json"))
