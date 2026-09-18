"""Isolated, file-based SQLite database per test — same pattern as
``tests/api/conftest.py`` (see that file's docstring for the rationale).
Duplicated here rather than shared because these tests exercise
``app.mqtt.service`` directly (monkeypatching its ``SessionLocal``), not
the FastAPI app/``get_db`` dependency the API tests need a ``TestClient``
for.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import models  # noqa: F401  (side effect: registers tables on Base.metadata)
from app.db.base import Base


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
