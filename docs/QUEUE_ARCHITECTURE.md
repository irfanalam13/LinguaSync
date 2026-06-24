# QUEUE ARCHITECTURE (Phase 5 — Step 5)

> Verified via the eager backend (flow tests run jobs through the queue inline).

## Design
`JobQueue.enqueue(job_id)` with two backends (`VC_QUEUE_BACKEND`):
- **`eager`** (dev/tests) — runs `worker.run_job` inline, no Redis. The job is complete by
  the time the create-job request returns.
- **`rq`** (prod) — enqueues `app.jobs.worker.run_job` onto a Redis-backed RQ queue; one or
  more `worker.py` processes consume it.

## Features
- **Queue jobs** — `POST /api/v1/jobs` creates a `Job` row (status `queued`) then enqueues.
- **Track progress** — worker updates `Job.progress`/`stage`/`status` in the DB (surfaced via
  the jobs API + WebSocket).
- **Cancel** — `DELETE /api/v1/jobs/{id}`: queued/running → status `cancelled` (+ `queue.cancel`
  for RQ); terminal → deleted.
- **Retry** — re-enqueue a failed job (API hook; RQ also supports automatic retries).

## Redis via Docker (prod-like)
```bash
docker run -d --name voice-redis -p 6379:6379 redis:7
pip install rq redis   # backend env only
export VC_QUEUE_BACKEND=rq VC_REDIS_URL=redis://localhost:6379/0
python worker.py       # in a second process
```

## Files
`app/jobs/queue.py` (`EagerQueue`, `RQQueue`, `get_queue`), `worker.py` (RQ entrypoint).
