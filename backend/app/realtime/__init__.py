"""WebSocket layer for pushing live state updates to the frontend.

Implemented in Milestone 6: a small in-memory ``ConnectionManager``
(``manager.py``) plus a minimal JSON event envelope (``events.py``).
This module is a pure realtime *delivery* mechanism — it never
persists anything and never makes coordination decisions; it is called
from ``app.mqtt.service`` (new telemetry) and
``app.api.routes.coordination`` (a completed coordination run) after
those already do the real persistence/decision work, and from
``app.api.routes.websocket`` (the WebSocket endpoint itself).
"""

from app.realtime.events import coordination_completed_event, telemetry_updated_event
from app.realtime.manager import ConnectionManager, manager

__all__ = [
    "ConnectionManager",
    "coordination_completed_event",
    "manager",
    "telemetry_updated_event",
]
