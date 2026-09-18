"""Policy resource endpoints."""

from fastapi import APIRouter, status

from app.api.deps import DbSession
from app.db import repository as repo
from app.domain import Policy

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[Policy])
def list_policies(db: DbSession) -> list[Policy]:
    return repo.list_policies(db)


@router.post("", response_model=Policy, status_code=status.HTTP_201_CREATED)
def create_policy(payload: Policy, db: DbSession) -> Policy:
    return repo.create_policy(db, payload)
