"""WebSocket live job-progress tracking.

Client connects to ``/api/v1/ws/jobs/{job_id}?token=<access_jwt>`` and receives JSON
progress frames until the job reaches a terminal state. Auth is via the access token in
the query string (browsers can't set WS headers). Progress is polled from the DB; for
multi-worker scale this would move to Redis pub/sub (documented in WEBSOCKET_ARCHITECTURE.md).
"""

from __future__ import annotations

import asyncio

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core import security
from app.db.base import SessionLocal
from app.db.models.job import Job, JobStatus

router = APIRouter(tags=["ws"])

_TERMINAL = {JobStatus.completed.value, JobStatus.failed.value, JobStatus.cancelled.value}


def _job_frame(job: Job) -> dict:
    return {
        "job_id": job.id, "status": job.status, "progress": job.progress,
        "stage": job.stage, "similarity": job.similarity, "error": job.error,
    }


@router.websocket("/api/v1/ws/jobs/{job_id}")
async def ws_job_progress(websocket: WebSocket, job_id: str, token: str = "") -> None:
    # Authenticate before accepting (close with policy-violation on failure).
    try:
        payload = security.decode_token(token, expected_type=security.ACCESS)
        user_id = payload["sub"]
    except (jwt.PyJWTError, KeyError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                job = db.get(Job, job_id)
            finally:
                db.close()
            if job is None or job.user_id != user_id:
                await websocket.send_json({"error": "job not found"})
                break
            await websocket.send_json(_job_frame(job))
            if job.status in _TERMINAL:
                break
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
