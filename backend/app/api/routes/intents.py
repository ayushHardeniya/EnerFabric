"""Intent resource endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.db import repository as repo
from app.db.errors import NotFoundError
from app.domain import Intent

router = APIRouter(prefix="/intents", tags=["intents"])


@router.get("", response_model=list[Intent])
def list_intents(db: DbSession, asset_id: str | None = None) -> list[Intent]:
    return repo.list_intents(db, asset_id=asset_id)


@router.post("", response_model=Intent, status_code=status.HTTP_201_CREATED)
def create_intent(payload: Intent, db: DbSession) -> Intent:
    try:
        return repo.create_intent(db, payload)
    except NotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
