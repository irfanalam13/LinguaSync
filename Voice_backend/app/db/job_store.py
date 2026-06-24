"""Minimal in-memory job store for status tracking.

A thread-safe dict keyed by job id. This is deliberately simple for Phase 2 (single
process); it can be swapped for a real DB without changing callers.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Dict, Optional


@dataclass
class Job:
    job_id: str
    status: str = "pending"  # pending | running | completed | failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)


class JobStore:
    def __init__(self) -> None:
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, job_id: str, **meta: Any) -> Job:
        with self._lock:
            job = Job(job_id=job_id, meta=meta)
            self._jobs[job_id] = job
            return job

    def update(self, job_id: str, **fields: Any) -> Job:
        with self._lock:
            job = self._jobs[job_id]
            for k, v in fields.items():
                setattr(job, k, v)
            return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)


@lru_cache(maxsize=1)
def get_job_store() -> JobStore:
    return JobStore()
