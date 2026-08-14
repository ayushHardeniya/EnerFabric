"""Asset resource endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DbSession
from app.api.schemas import AssetCreate
from app.db import repository as repo
from app.domain import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset])
def list_assets(db: DbSession) -> list[Asset]:
    return repo.list_assets(db)


@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: str, db: DbSession) -> Asset:
    asset = repo.get_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"asset '{asset_id}' not found")
    return asset


@router.post("", response_model=Asset, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: DbSession) -> Asset:
    asset = Asset(name=payload.name, type=payload.type, capabilities=payload.capabilities)
    return repo.create_asset(db, asset)
