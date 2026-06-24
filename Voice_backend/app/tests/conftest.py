"""Backend test fixtures.

Env vars are set BEFORE any app import so the global engine/storage/queue resolve to
test-safe backends (temp SQLite file, local storage, eager queue). This lets the eager
worker (which uses the global SessionLocal) and the API share one database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="vc_backend_test_"))
os.environ.setdefault("VC_DATABASE_URL", f"sqlite:///{(_TMP / 'test.db').as_posix()}")
os.environ.setdefault("VC_STORAGE_BACKEND", "local")
os.environ.setdefault("VC_STORAGE_DIR", _TMP.joinpath("storage").as_posix())
os.environ.setdefault("VC_QUEUE_BACKEND", "eager")
os.environ.setdefault("VC_UPLOADS_DIR", _TMP.joinpath("uploads").as_posix())
os.environ.setdefault("VC_LOGS_DIR", _TMP.joinpath("logs").as_posix())

import pytest  # noqa: E402

from app.core.config import Settings  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    """Create all tables on the global (temp) engine once."""
    from app.db.session import create_all

    create_all()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Ad-hoc Settings with tmp dirs (used by legacy direct-HTTP API tests)."""
    s = Settings(uploads_dir=tmp_path / "uploads", logs_dir=tmp_path / "logs")
    s.ensure_dirs()
    return s
