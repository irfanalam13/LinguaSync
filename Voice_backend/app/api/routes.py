"""Public API routes — gateway to the Voice_ML inference service.

The backend handles uploads, job tracking and status; it delegates ALL inference
to Voice_ML over HTTP (``app.jobs.ml_client``). No ML libraries are imported here.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.db.job_store import get_job_store
from app.jobs.ml_client import MLServiceError, get_ml_client
from app.schemas.api import JobStatusResponse, TranslateResponse
from shared.contracts import MLTranslateRequest
from shared.languages import LANGUAGES
import uuid

router = APIRouter(prefix="/api/v1", tags=["translation"])


def _new_job_id() -> str:
    return uuid.uuid4().hex[:12]


@router.get("/health")
def health() -> dict:
    """Backend health + ML service reachability."""
    client = get_ml_client()
    ml_ok, ml_info = True, {}
    try:
        ml_info = client.health()
    except MLServiceError as e:
        ml_ok, ml_info = False, {"error": str(e)}
    return {"status": "ok", "service": "voice_backend", "ml_reachable": ml_ok, "ml": ml_info}


@router.post("/translate", response_model=TranslateResponse)
async def translate_video(
    file: UploadFile = File(..., description="Input video file"),
    target: str = Form(..., description="Target language: en or ne"),
    source: str | None = Form(None, description="Optional forced source language"),
    preserve_voice: bool = Form(False, description="Phase 2: preserve original speaker"),
    clone_voice: bool = Form(False, description="Phase 3: clone the speaker's identity"),
    localize: bool = Form(False, description="Phase 4: clone + lip-sync (full localization)"),
) -> TranslateResponse:
    settings = get_settings()
    settings.ensure_dirs()

    if target not in LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported target '{target}'.")
    if source is not None and source not in LANGUAGES:
        raise HTTPException(status_code=422, detail=f"Unsupported source '{source}'.")

    job_id = _new_job_id()
    suffix = Path(file.filename or "input.mp4").suffix or ".mp4"
    upload_path = (settings.uploads_dir / f"{job_id}{suffix}").resolve()
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()
    if upload_path.stat().st_size == 0:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    store = get_job_store()
    store.create(job_id, target=target, source=source,
                 preserve_voice=preserve_voice, clone_voice=clone_voice, localize=localize)
    store.update(job_id, status="running")

    req = MLTranslateRequest(
        video_path=str(upload_path),
        target_language=target,
        source_language=source,
        preserve_voice=preserve_voice,
        clone_voice=clone_voice,
        localize=localize,
        job_id=job_id,
    )
    try:
        ml = get_ml_client().translate(req)
    except MLServiceError as e:
        store.update(job_id, status="failed", error=str(e))
        raise HTTPException(status_code=502, detail=str(e)) from e

    store.update(job_id, status="completed", result=ml.model_dump())

    return TranslateResponse(
        job_id=ml.job_id,
        status="completed",
        output_video=ml.output_video,
        source_language=ml.source_language,
        target_language=ml.target_language,
        preserve_voice=ml.preserve_voice,
        similarity=ml.similarity,
        timings=ml.timings,
    )

# NOTE: legacy GET /jobs/{id} (in-memory job store) removed in Phase 5 — superseded by the
# DB-backed, authenticated jobs API in app/api/jobs.py.
