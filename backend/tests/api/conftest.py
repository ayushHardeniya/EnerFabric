"""Shared fixtures for API/DB tests.

Each test gets an isolated, file-based SQLite database — schema built
directly from the ORM ``Base.metadata``, not through Alembic (Alembic's
job is the real PostgreSQL schema; these tests exercise the app's
repository/route logic against the same ``app/db/models.py`` models,
not re-validate the migration file itself). File-based rather than
in-memory so that separate ``Session`` objects — one per simulated
request, mirroring real request lifecycles via the ``get_db``
dependency override below — still see the same data; that's what makes
a "persistence across sessions" test meaningful rather than trivial.

This keeps the test suite fully self-contained (no external/cloud
database, no Docker requirement) while still exercising the real
SQLAlchemy models end to end.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401  (side effect: registers tables on Base.metadata)
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    test_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def _enable_sqlite_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
