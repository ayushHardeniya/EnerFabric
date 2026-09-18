"""Database engine/session configuration.

Sync SQLAlchemy (not asyncio) — chosen for Milestone 4 simplicity: FastAPI
runs sync ``def`` route handlers in a threadpool automatically, so a sync
engine avoids async-session/greenlet complexity for no real benefit at
this MVP's scale. ``DATABASE_URL`` is read from application settings
(environment variables / ``.env``), never hard-coded.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields one request-scoped session, always closed after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
