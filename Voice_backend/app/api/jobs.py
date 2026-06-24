"""Translation-job routes: create (→queue), get, list, cancel, download result."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.job import Job, JobStatus
from app.db.models.user import User
from app.db.models.video import Video
from app.db.session import get_db
from app.jobs.queue import get_queue
from app.schemas.job import JobCreate, JobPublic
from app.services.storage import get_storage

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


def _owned(db: Session, user: User, job_id: str) -> Job:
    j = db.scalar(select(Job).where(Job.id == job_id, Job.user_id == user.id))
    if j is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return j


@router.post("", response_model=JobPublic, status_code=201)
def create_job(body: JobCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Job:
    video = db.scalar(select(Video).where(Video.id == body.video_id, Video.user_id == user.id))
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if body.source_language and body.source_language == body.target_language:
        raise HTTPException(status_code=422, detail="Source and target languages must differ")

    job = Job(
        user_id=user.id, video_id=video.id, target_language=body.target_language,
        source_language=body.source_language, mode=body.mode.value, status=JobStatus.queued.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    queue_job_id = get_queue().enqueue(job.id)  # eager runs inline here
    if queue_job_id:
        job.queue_job_id = queue_job_id
        db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobPublic])
def list_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(Job).where(Job.user_id == user.id).order_by(Job.created_at.desc())))


@router.get("/{job_id}", response_model=JobPublic)
def get_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Job:
    return _owned(db, user, job_id)


@router.delete("/{job_id}", status_code=204)
def cancel_or_delete_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _owned(db, user, job_id)
    if job.status in (JobStatus.queued.value, JobStatus.running.value):
        if job.queue_job_id:
            get_queue().cancel(job.queue_job_id)
        job.status = JobStatus.cancelled.value
        db.commit()
    else:
        db.delete(job)
        db.commit()


@router.get("/{job_id}/result")
def download_result(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = _owned(db, user, job_id)
    if job.status != JobStatus.completed.value or not job.result_key:
        raise HTTPException(status_code=409, detail="Result not ready")
    dest = Path(tempfile.mkdtemp(prefix="dl_")) / "final_output.mp4"
    get_storage().get_file(job.result_key, dest)
    return FileResponse(str(dest), media_type="video/mp4", filename=f"localized_{job_id}.mp4")
