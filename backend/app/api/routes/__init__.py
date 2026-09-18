"""Individual route modules, one per resource, aggregated into a single
router mounted under the configured API prefix in ``app.main``.
"""

from fastapi import APIRouter

from app.api.routes import assets, coordination, intents, policies, telemetry, websocket

router = APIRouter()
router.include_router(assets.router)
router.include_router(telemetry.router)
router.include_router(intents.router)
router.include_router(policies.router)
router.include_router(coordination.router)
router.include_router(websocket.router)

__all__ = ["router"]
