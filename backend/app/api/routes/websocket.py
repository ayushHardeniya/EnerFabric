"""Realtime WebSocket endpoint.

A thin delivery mechanism only: on connect, register the client with
the shared ``ConnectionManager``; clients then just receive whatever
JSON events (see ``app.realtime.events``) get broadcast to them. No
business/coordination logic lives here, and nothing the client sends
is acted on — inbound messages are read only to detect disconnects.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("websocket connection closed unexpectedly")
    finally:
        manager.disconnect(websocket)
