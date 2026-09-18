"""FastAPI application entrypoint.

Mounts the health check plus the Milestone 4 resource routers (assets,
telemetry, intents, policies, coordination) and the Milestone 6 WebSocket
endpoint, under the configured API prefix. The Milestone 5 MQTT telemetry
subscriber is started/stopped via the lifespan context below — a
connection failure at startup (e.g. no Mosquitto reachable) is logged, not
raised, so the REST API keeps serving even without live MQTT ingestion
(see ``app.mqtt.service``).
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.mqtt.service import build_telemetry_subscriber
from app.mqtt.subscriber import TelemetrySubscriber
from app.realtime import manager as ws_manager

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Bound first: MQTT (its own background thread) and sync route
    # handlers (FastAPI's threadpool) both broadcast via
    # ``broadcast_threadsafe``, which needs this loop reference to
    # schedule work back onto it.
    ws_manager.bind_loop(asyncio.get_running_loop())
    subscriber: TelemetrySubscriber | None = None
    if settings.mqtt_enabled:
        subscriber = build_telemetry_subscriber()
        try:
            subscriber.start()
        except OSError:
            logger.warning(
                "MQTT broker unreachable at %s:%s — starting without live telemetry ingestion",
                settings.mqtt_broker_host,
                settings.mqtt_broker_port,
            )
            subscriber = None
    yield
    if subscriber is not None:
        subscriber.stop()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(ValidationError)
async def domain_validation_exception_handler(
    _request: Request, exc: ValidationError
) -> JSONResponse:
    """Some routes construct a domain model (with its own cross-field
    invariants, e.g. Asset's no-duplicate-capability-types check) from an
    already-parsed request schema inside the handler body, one step after
    FastAPI's own request validation. A failure there is still a client
    input problem, not a server error, so it's translated to the same 422
    shape FastAPI uses for request validation errors.
    """
    return JSONResponse(status_code=422, content=jsonable_encoder({"detail": exc.errors()}))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
