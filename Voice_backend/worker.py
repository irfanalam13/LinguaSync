"""RQ worker entrypoint (production job consumer).

Run alongside the API to process queued jobs:

    cd Voice_backend
    VC_QUEUE_BACKEND=rq VC_REDIS_URL=redis://localhost:6379/0 python worker.py

Each job runs ``app.jobs.worker.run_job`` (pull video → call Voice_ML → store result →
update DB). In dev/tests the queue is ``eager`` and no worker process is needed.
"""

from __future__ import annotations

import sys

from app.core.config import get_settings


def main() -> int:
    settings = get_settings()
    try:
        from redis import Redis
        from rq import Queue, Worker
    except ImportError:
        print("RQ/redis not installed. `pip install rq redis` to run the worker.", file=sys.stderr)
        return 1

    conn = Redis.from_url(settings.redis_url)
    queue = Queue(settings.job_queue_name, connection=conn)
    print(f"[worker] consuming '{settings.job_queue_name}' on {settings.redis_url}")
    Worker([queue], connection=conn).work(with_scheduler=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
