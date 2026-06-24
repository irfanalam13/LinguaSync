"""Video schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VideoPublic(BaseModel):
    id: str
    filename: str
    content_type: Optional[str] = None
    size_bytes: int
    duration_s: Optional[float] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
