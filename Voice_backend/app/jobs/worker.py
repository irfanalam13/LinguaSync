"""Job worker: consume a job, run the Voice_ML pipeline, store the result, update status.

This is the function the queue executes (eager inline, or via an RQ worker process). It
is storage- and transport-agnostic: it pulls the source video from object storage, calls
the Voice_ML inference service over HTTP, then uploads the produced video back to storage.
No ML runs in this process — inference stays in Voice_ML.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.db.base import SessionLocal
from app.db.models.job import Job, JobMode, JobStatus
from app.db.models.mixins import utcnow
from app.db.models.video import Video
from app.jobs.ml_client import MLServiceError, get_ml_client
from app.services.storage import get_storage
from shared.contracts import MLTranslateRequest
from shared.logging import get_logger

log = get_logger("jobs.worker")

# Job.mode → Voice_ML request flags.
_MODE_FLAGS = {
    JobMode.translate.value: {},
    JobMode.preserve.value: {"preserve_voice": True},
    JobMode.clone.value: {"clone_voice": True},
    JobMode.localize.value: {"localize": True},
}


def _set(db, job: Job, **fields) -> None:
    for k, v in fields.items():
        setattr(job, k, v)
    db.commit()


def run_job(job_id: str) -> dict:
    """Execute one job end-to-end. Returns a small status dict (also persisted)."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            log.warning("run_job: unknown job %s", job_id)
            return {"job_id": job_id, "status": "unknown"}

        _set(db, job, status=JobStatus.running.value, started_at=utcnow(), progress=5, stage="starting")
        video = db.get(Video, job.video_id)
        if video is None:
            raise RuntimeError("source video not found")

        storage = get_storage()
        tmpdir = Path(tempfile.mkdtemp(prefix=f"job_{job_id}_"))
        local_in = tmpdir / Path(video.storage_key).name
        _set(db, job, progress=10, stage="fetching video")
        storage.get_file(video.storage_key, local_in)

        req = MLTranslateRequest(
            video_path=str(local_in),
            target_language=job.target_language,
            source_language=job.source_language,
            job_id=job.id,
            **_MODE_FLAGS.get(job.mode, {}),
        )
        _set(db, job, progress=20, stage="inference")
        result = get_ml_client().translate(req)

        _set(db, job, progress=90, stage="storing result")
        result_key = f"results/{job_id}/final_output.mp4"
        storage.put_file(result_key, result.output_video, content_type="video/mp4")

        _set(
            db, job,
            status=JobStatus.completed.value, progress=100, stage="done",
            result_key=result_key, similarity=result.similarity, finished_at=utcnow(),
        )
        log.info("job %s completed (similarity=%s)", job_id, result.similarity)
        return {"job_id": job_id, "status": "completed", "result_key": result_key}

    except (MLServiceError, Exception) as e:  # noqa: BLE001 - record any failure
        log.exception("job %s failed", job_id)
        try:
            job = db.get(Job, job_id)
            if job and job.status != JobStatus.cancelled.value:
                _set(db, job, status=JobStatus.failed.value, error=str(e)[:2000], finished_at=utcnow())
        except Exception:
            db.rollback()
        return {"job_id": job_id, "status": "failed", "error": str(e)}
    finally:
        db.close()
