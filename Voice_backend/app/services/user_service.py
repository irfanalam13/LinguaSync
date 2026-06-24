"""User-management business logic: profile, usage stats, API keys."""

from __future__ import annotations

import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security
from app.db.models.job import Job, JobStatus
from app.db.models.user import ApiKey, User
from app.db.models.video import Video
from app.schemas.user import UsageStats

_API_KEY_PREFIX = "vc_"


def update_profile(db: Session, user: User, full_name=None, avatar_url=None) -> User:
    if full_name is not None:
        user.full_name = full_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    db.commit()
    db.refresh(user)
    return user


def usage_stats(db: Session, user: User) -> UsageStats:
    def _count(stmt):
        return db.scalar(stmt) or 0

    videos = _count(select(func.count()).select_from(Video).where(Video.user_id == user.id))
    by_status = {
        s.value: _count(
            select(func.count()).select_from(Job).where(Job.user_id == user.id, Job.status == s.value)
        )
        for s in JobStatus
    }
    total = _count(select(func.count()).select_from(Job).where(Job.user_id == user.id))
    return UsageStats(
        videos=videos,
        jobs_total=total,
        jobs_completed=by_status["completed"],
        jobs_failed=by_status["failed"],
        jobs_running=by_status["running"],
        jobs_queued=by_status["queued"],
    )


def create_api_key(db: Session, user: User, name: str) -> tuple[ApiKey, str]:
    """Create an API key; returns (record, raw_key). The raw key is shown only once."""
    raw = _API_KEY_PREFIX + secrets.token_urlsafe(32)
    prefix = raw[:10]
    record = ApiKey(
        user_id=user.id, name=name, prefix=prefix, hashed_key=security.hash_password(raw)
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, raw


def list_api_keys(db: Session, user: User) -> list[ApiKey]:
    return list(db.scalars(select(ApiKey).where(ApiKey.user_id == user.id).order_by(ApiKey.created_at.desc())))


def revoke_api_key(db: Session, user: User, key_id: str) -> bool:
    rec = db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    if not rec:
        return False
    rec.is_active = False
    db.commit()
    return True


def authenticate_api_key(db: Session, raw_key: str) -> User | None:
    """Resolve a raw API key to its active user (prefix lookup + hash verify)."""
    if not raw_key.startswith(_API_KEY_PREFIX):
        return None
    prefix = raw_key[:10]
    for rec in db.scalars(select(ApiKey).where(ApiKey.prefix == prefix, ApiKey.is_active.is_(True))):
        if security.verify_password(raw_key, rec.hashed_key):
            return db.get(User, rec.user_id)
    return None
