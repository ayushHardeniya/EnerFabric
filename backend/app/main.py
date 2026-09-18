"""FastAPI application entrypoint.

Mounts the health check plus the Milestone 4 resource routers (assets,
telemetry, intents, policies, coordination) under the configured API
prefix.
"""

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.routes import router as api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)
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
