"""Filesystem helpers: per-job artifact directories and small writers."""

from __future__ import annotations

import uuid
from pathlib import Path


def new_job_id() -> str:
    """Short, collision-resistant job id."""
    return uuid.uuid4().hex[:12]


def job_artifacts_dir(artifacts_root: Path, job_id: str) -> Path:
    """Create and return ``<artifacts_root>/<job_id>/`` for per-job isolation."""
    d = Path(artifacts_root) / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_text(path: Path, content: str) -> Path:
    """Write UTF-8 text, creating parent dirs as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
