"""Shared fixtures for realtime/WebSocket tests.

Same isolated, file-based SQLite database strategy as
``tests/api/conftest.py`` (see that file's docstring for the full
rationale), with one addition: ``client`` here enters ``TestClient(app)``
as a context manager so the app's real ``lifespan`` actually runs — that
is what binds ``ConnectionManager``'s event loop
(``app.realtime.manager.manager.bind_loop``), exactly as happens in
production. Without it, ``broadcast_threadsafe`` would silently no-op.
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
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
