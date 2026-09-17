"""FastAPI application entrypoint.

At Milestone 0 this exposes only a health check, so the foundation is
verifiably runnable end to end. Domain routers are mounted starting
Milestone 4.
"""

from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name, "environment": settings.environment}
