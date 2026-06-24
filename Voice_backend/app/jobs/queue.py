"""Job queue abstraction: eager (dev/tests) or RQ (production).

- ``eager``: runs ``worker.run_job`` inline — no Redis needed; great for dev/tests.
- ``rq``: enqueues onto a Redis-backed RQ queue consumed by ``worker.py`` processes.

The caller (job API) only sees ``enqueue(job_id)`` / ``cancel(queue_job_id)``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.core.config import get_settings
from app.jobs.worker import run_job
from shared.logging import get_logger

log = get_logger("jobs.queue")


class JobQueue:
    def enqueue(self, job_id: str) -> Optional[str]:  # returns queue job id (rq) or None (eager)
        raise NotImplementedError

    def cancel(self, queue_job_id: str) -> bool:
        return False


class EagerQueue(JobQueue):
    def enqueue(self, job_id: str) -> Optional[str]:
        log.info("eager-executing job %s", job_id)
        run_job(job_id)
        return None


class RQQueue(JobQueue):  # pragma: no cover - exercised only with a live Redis
    def __init__(self):
        from redis import Redis
        from rq import Queue

        s = get_settings()
        self._q = Queue(s.job_queue_name, connection=Redis.from_url(s.redis_url))

    def enqueue(self, job_id: str) -> Optional[str]:
        job = self._q.enqueue("app.jobs.worker.run_job", job_id, job_timeout=3600)
        return job.id

    def cancel(self, queue_job_id: str) -> bool:
        try:
            from rq.job import Job as RQJob

            RQJob.fetch(queue_job_id, connection=self._q.connection).cancel()
            return True
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_queue() -> JobQueue:
    backend = get_settings().queue_backend
    if backend == "rq":
        log.info("queue backend: RQ (%s)", get_settings().redis_url)
        return RQQueue()
    log.info("queue backend: eager (inline)")
    return EagerQueue()
