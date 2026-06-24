"""Video upload/management routes."""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models.user import User
from app.db.models.video import Video
from app.db.session import get_db
from app.schemas.video import VideoPublic
from app.services.storage import get_storage

router = APIRouter(prefix="/api/v1/videos", tags=["videos"])

_ALLOWED_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


@router.post("/upload", response_model=VideoPublic, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Video:
    settings = get_settings()
    ext = Path(file.filename or "video.mp4").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(status_code=422, detail=f"Unsupported file type '{ext}'. Allowed: {sorted(_ALLOWED_EXT)}")

    video_id = uuid.uuid4().hex
    key = f"videos/{user.id}/{video_id}{ext}"

    # Stream to a temp file, enforce size cap, then hand to storage.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    _fd, _tmp_name = tempfile.mkstemp(suffix=ext)
    os.close(_fd)  # close the mkstemp handle so Windows can reopen/unlink it
    tmp = Path(_tmp_name)
    size = 0
    try:
        with open(tmp, "wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
                out.write(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="Uploaded file is empty")
        get_storage().put_file(key, tmp, content_type=file.content_type)
    finally:
        tmp.unlink(missing_ok=True)
        await file.close()

    video = Video(
        id=video_id, user_id=user.id, filename=file.filename or f"{video_id}{ext}",
        storage_key=key, content_type=file.content_type, size_bytes=size,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


def _owned(db: Session, user: User, video_id: str) -> Video:
    v = db.scalar(select(Video).where(Video.id == video_id, Video.user_id == user.id))
    if v is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return v


@router.get("", response_model=list[VideoPublic])
def list_videos(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return list(db.scalars(
        select(Video).where(Video.user_id == user.id, Video.status != "deleted").order_by(Video.created_at.desc())
    ))


@router.get("/{video_id}", response_model=VideoPublic)
def get_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Video:
    return _owned(db, user, video_id)


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    v = _owned(db, user, video_id)
    try:
        get_storage().delete(v.storage_key)
    except Exception:
        pass  # best-effort; remove the record regardless
    db.delete(v)
    db.commit()
