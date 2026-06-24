"""Password hashing (bcrypt) and JWT token helpers.

bcrypt is used directly (not via passlib) for clean compatibility with bcrypt 5.x.
JWTs carry a ``type`` claim (access | refresh | reset | verify) so a token issued for
one purpose can't be replayed for another. Refresh tokens also carry a ``jti`` for
server-side revocation (see auth_service).
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any, Optional

import bcrypt
import jwt

from app.core.config import get_settings
from app.db.models.mixins import utcnow

ACCESS = "access"
REFRESH = "refresh"
RESET = "reset"
VERIFY = "verify"

# bcrypt input is limited to 72 bytes; longer passwords are pre-hashed-safe by truncation.
_BCRYPT_MAX = 72


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:_BCRYPT_MAX]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:_BCRYPT_MAX], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _encode(claims: dict[str, Any], expires: timedelta) -> str:
    s = get_settings()
    now = utcnow()
    payload = {**claims, "iat": now, "exp": now + expires}
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str, expected_type: Optional[str] = None) -> dict[str, Any]:
    """Decode + validate a JWT. Raises ``jwt.PyJWTError`` on failure/expiry/type-mismatch."""
    s = get_settings()
    payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    if expected_type is not None and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token, got {payload.get('type')}")
    return payload


def create_access_token(user_id: str) -> str:
    s = get_settings()
    return _encode({"sub": user_id, "type": ACCESS}, timedelta(minutes=s.access_token_ttl_min))


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Return (token, jti). The jti is stored server-side for revocation."""
    s = get_settings()
    jti = uuid.uuid4().hex
    token = _encode({"sub": user_id, "type": REFRESH, "jti": jti},
                    timedelta(days=s.refresh_token_ttl_days))
    return token, jti


def create_purpose_token(user_id: str, purpose: str, ttl_min: int = 60) -> str:
    assert purpose in (RESET, VERIFY)
    return _encode({"sub": user_id, "type": purpose}, timedelta(minutes=ttl_min))
