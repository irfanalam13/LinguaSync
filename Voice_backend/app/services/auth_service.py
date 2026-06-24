"""Authentication business logic (register, login, refresh, reset, verify).

Refresh tokens are persisted (by jti) so logout/rotation can revoke them. Password-reset
and email-verify use short-lived purpose-scoped JWTs (email delivery is a hook — the token
is returned/logged here; wiring an email provider is a later concern, not inference).
"""

from __future__ import annotations

from datetime import timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from shared.logging import get_logger
from app.db.models.mixins import utcnow
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User

log = get_logger("services.auth")


class AuthError(Exception):
    """Authentication/authorization failure (mapped to 401/409 by the API)."""


class ConflictError(AuthError):
    """Resource already exists (e.g. duplicate email)."""


def register(db: Session, email: str, password: str, full_name: str | None) -> User:
    email = email.lower().strip()
    if db.scalar(select(User).where(User.email == email)):
        raise ConflictError("Email already registered.")
    user = User(email=email, hashed_password=security.hash_password(password), full_name=full_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    log.info("registered user %s", user.id)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user or not security.verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.")
    if not user.is_active:
        raise AuthError("Account is disabled.")
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    """Create an access token + a persisted refresh token."""
    access = security.create_access_token(user.id)
    refresh, jti = security.create_refresh_token(user.id)
    db.add(RefreshToken(
        user_id=user.id, jti=jti,
        expires_at=utcnow() + timedelta(days=get_settings().refresh_token_ttl_days),
    ))
    db.commit()
    return access, refresh


def refresh_tokens(db: Session, refresh_token: str) -> tuple[str, str]:
    """Validate + rotate a refresh token (old jti revoked, new pair issued)."""
    try:
        payload = security.decode_token(refresh_token, expected_type=security.REFRESH)
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid refresh token: {e}") from e

    jti = payload.get("jti")
    rec = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if rec is None or rec.revoked:
        raise AuthError("Refresh token revoked or unknown.")

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise AuthError("User not found or disabled.")

    rec.revoked = True  # rotate
    db.commit()
    return issue_tokens(db, user)


def logout(db: Session, refresh_token: str) -> None:
    """Revoke a refresh token (best-effort; idempotent)."""
    try:
        payload = security.decode_token(refresh_token, expected_type=security.REFRESH)
    except jwt.PyJWTError:
        return
    rec = db.scalar(select(RefreshToken).where(RefreshToken.jti == payload.get("jti")))
    if rec and not rec.revoked:
        rec.revoked = True
        db.commit()


def create_password_reset_token(db: Session, email: str) -> str | None:
    """Return a reset token if the email exists (caller emails it); None otherwise."""
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if not user:
        return None  # do not reveal existence
    return security.create_purpose_token(user.id, security.RESET, ttl_min=30)


def confirm_password_reset(db: Session, token: str, new_password: str) -> None:
    try:
        payload = security.decode_token(token, expected_type=security.RESET)
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid or expired reset token: {e}") from e
    user = db.get(User, payload["sub"])
    if not user:
        raise AuthError("User not found.")
    user.hashed_password = security.hash_password(new_password)
    # Revoke all refresh tokens on password change.
    for rec in db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)):
        rec.revoked = True
    db.commit()


def create_email_verify_token(user: User) -> str:
    return security.create_purpose_token(user.id, security.VERIFY, ttl_min=60 * 24)


def confirm_email_verification(db: Session, token: str) -> User:
    try:
        payload = security.decode_token(token, expected_type=security.VERIFY)
    except jwt.PyJWTError as e:
        raise AuthError(f"Invalid or expired verification token: {e}") from e
    user = db.get(User, payload["sub"])
    if not user:
        raise AuthError("User not found.")
    user.is_verified = True
    db.commit()
    return user
