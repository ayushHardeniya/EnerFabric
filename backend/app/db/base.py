"""Shared SQLAlchemy declarative base for all ORM models.

Kept separate from ``models.py`` so Alembic's ``env.py`` can import the
metadata without importing the (heavier) model definitions module
directly, and so ``session.py`` doesn't need to import the full model
set just to create an engine.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
