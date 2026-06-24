"""Job schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models.job import JobMode

SUPPORTED_LANGS = {"en", "ne"}


class JobCreate(BaseModel):
    video_id: str
    target_language: str = Field(pattern="^(en|ne)$")
    source_language: Optional[str] = Field(default=None, pattern="^(en|ne)$")
    mode: JobMode = JobMode.translate


class JobPublic(BaseModel):
    id: str
    video_id: str
    target_language: str
    source_language: Optional[str] = None
    mode: str
    status: str
    progress: int
    stage: Optional[str] = None
    similarity: Optional[float] = None
    result_key: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
