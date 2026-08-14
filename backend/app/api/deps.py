"""Shared FastAPI dependency types for route handlers.

``DbSession`` is the modern ``Annotated``-based dependency pattern
(recommended by FastAPI) rather than a ``Depends(get_db)`` default
argument value in every handler signature — this also sidesteps
ruff's B008 (no function calls in argument defaults), which a bare
``Depends(...)`` default would otherwise trigger on every route.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
