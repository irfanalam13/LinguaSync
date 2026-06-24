"""Request/response models for the public HTTP API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from shared.contracts import StageTimings


class TranslateResponse(BaseModel):
    """Response of ``POST /api/v1/translate``."""

    job_id: str
    status: str
    output_video: str
    source_language: str
    target_language: str
    preserve_voice: bool = False
    similarity: Optional[float] = None
    timings: Optional[StageTimings] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    status: str = "failed"
    error: str
    detail: Optional[str] = None
