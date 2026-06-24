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

_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    _settings.database_url,
    echo=_settings.db_echo,
    future=True,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
