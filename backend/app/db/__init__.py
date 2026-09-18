"""Database layer: SQLAlchemy models, session management, and PostgreSQL
persistence.

- ``base.py``     — shared declarative Base.
- ``models.py``   — ORM models mirroring the persisted domain concepts.
- ``session.py``  — engine/session configuration and the ``get_db`` FastAPI dependency.
- ``repository.py`` — the only place that converts between ORM rows and
  ``app.domain`` models; the API layer only ever sees domain objects.
- ``errors.py``   — persistence-layer exceptions (e.g. ``NotFoundError``).

Schema is managed by Alembic (see ``backend/alembic/``), not
``Base.metadata.create_all()``, for anything other than isolated test
databases.
"""
