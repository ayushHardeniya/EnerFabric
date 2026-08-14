"""Telemetry resource endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.db import repository as repo
from app.db.errors import NotFoundError
from app.domain import Telemetry

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get("", response_model=list[Telemetry])
def list_telemetry(db: DbSession, asset_id: str | None = None) -> list[Telemetry]:
    return repo.list_telemetry(db, asset_id=asset_id)


@router.post("", response_model=Telemetry, status_code=status.HTTP_201_CREATED)
def create_telemetry(payload: Telemetry, db: DbSession) -> Telemetry:
    try:
        return repo.create_telemetry(db, payload)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
