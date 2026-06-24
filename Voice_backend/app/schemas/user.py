"""User-management schemas: profile, usage stats, API keys."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=120)
    avatar_url: Optional[str] = Field(default=None, max_length=512)


class UsageStats(BaseModel):
    videos: int
    jobs_total: int
    jobs_completed: int
    jobs_failed: int
    jobs_running: int
    jobs_queued: int


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ApiKeyPublic(BaseModel):
    id: str
    name: str
    prefix: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyPublic):
    key: str  # full key, shown ONCE at creation
