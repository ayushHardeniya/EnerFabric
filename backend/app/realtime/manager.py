"""Minimal in-memory WebSocket connection registry for a single process.

No Redis/pub-sub, no distributed state: broadcasting to every connected
client is just an async loop over local ``WebSocket`` objects, which is
all a single-process hackathon MVP needs. This class only tracks
connections and fans a JSON message out to them — it has no awareness
of telemetry, coordination, MQTT, or persistence (see ``app.realtime.events``
for the message shapes, and the callers in ``app.mqtt.service`` /
``app.api.routes.coordination`` for what triggers a broadcast).
"""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Record the running asyncio loop, called once from the app's
        lifespan startup. This is what lets ``broadcast_threadsafe`` be
        called from threads outside that loop — the MQTT subscriber's
        paho background thread, and FastAPI's threadpool for sync route
        handlers — without either of those needing to know anything
        about asyncio themselves.
        """
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for connection in list(self._connections):
            try:
                await connection.send_json(message)
            except Exception:
                logger.warning("dropping unresponsive websocket client")
                self.disconnect(connection)

    def broadcast_threadsafe(self, message: dict[str, Any]) -> None:
        """Schedule a broadcast from a thread that isn't running the
        asyncio loop (MQTT's background thread, or a sync FastAPI route
        handler running in the threadpool). A no-op before the loop has
        been bound (e.g. lifespan hasn't started yet) — realtime delivery
        is best-effort and must never block or fail the caller.
        """
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(message), self._loop)


manager = ConnectionManager()
