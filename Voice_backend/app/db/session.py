"""Database session dependency + table creation helper."""

from __future__ import annotations

from typing import Iterator

from sqlalchemy.orm import Session

from app.db.base import Base, SessionLocal, engine


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    """Create all tables (dev/tests; production uses Alembic migrations)."""
    import app.db.models  # noqa: F401  ensure models are registered

    Base.metadata.create_all(bind=engine)
