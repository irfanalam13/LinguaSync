"""SQLAlchemy 2.0 engine, session factory, and declarative base.

Sync engine (workers and FastAPI deps are sync). SQLite by default for dev/tests;
Postgres in production via ``VC_DATABASE_URL``. SQLite gets check_same_thread=False
so the dependency-injected session works across FastAPI's threadpool.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

_settings = get_settings()


def _normalize_url(url: str) -> str:
    """Use the psycopg (v3) driver for Postgres.

    Managed providers (Neon/Render/Heroku) hand out ``postgresql://…`` URLs, which
    SQLAlchemy maps to psycopg2 — often absent and unable to parse ``channel_binding``.
    Rewriting to ``postgresql+psycopg://`` uses psycopg v3 (installed via requirements)
    and supports Neon's ``sslmode``/``channel_binding`` query params.
    """
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):  # legacy scheme some providers still emit
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


_db_url = _normalize_url(_settings.database_url)
_connect_args = {"check_same_thread": False} if _db_url.startswith("sqlite") else {}

engine = create_engine(
    _db_url,
    echo=_settings.db_echo,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
