"""User-management routes: profile, usage, API keys."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import UserPublic
from app.schemas.user import ApiKeyCreate, ApiKeyCreated, ApiKeyPublic, ProfileUpdate, UsageStats
from app.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserPublic)
def get_profile(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserPublic)
def update_profile(
    body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> User:
    return user_service.update_profile(db, user, body.full_name, body.avatar_url)


@router.get("/me/usage", response_model=UsageStats)
def usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UsageStats:
    return user_service.usage_stats(db, user)


@router.post("/me/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    body: ApiKeyCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ApiKeyCreated:
    rec, raw = user_service.create_api_key(db, user, body.name)
    return ApiKeyCreated(
        id=rec.id, name=rec.name, prefix=rec.prefix, is_active=rec.is_active,
        created_at=rec.created_at, key=raw,
    )


@router.get("/me/api-keys", response_model=list[ApiKeyPublic])
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.list_api_keys(db, user)


@router.delete("/me/api-keys/{key_id}", status_code=204)
def revoke_api_key(key_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user_service.revoke_api_key(db, user, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
