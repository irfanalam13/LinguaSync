"""Authentication routes: register, login, refresh, logout, password reset, email verify."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.session import get_db
from app.services import auth_service as auth
from app.schemas.auth import (
    EmailVerifyConfirm,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = auth.register(db, body.email, body.password, body.full_name)
    except auth.ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    # (Email verification token generated here; delivery is a hook.)
    auth.create_email_verify_token(user)
    access, refresh = auth.issue_tokens(db, user)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = auth.authenticate(db, body.email, body.password)
    except auth.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    access, refresh = auth.issue_tokens(db, user)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        access, refresh_token = auth.refresh_tokens(db, body.refresh_token)
    except auth.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e
    return TokenResponse(access_token=access, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    auth.logout(db, body.refresh_token)


@router.post("/password-reset/request")
def password_reset_request(body: PasswordResetRequest, db: Session = Depends(get_db)) -> dict:
    token = auth.create_password_reset_token(db, body.email)
    # Always 200 (don't reveal whether the email exists). Token would be emailed.
    return {"message": "If the email exists, a reset link has been sent.", "reset_token": token}


@router.post("/password-reset/confirm", status_code=204)
def password_reset_confirm(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    try:
        auth.confirm_password_reset(db, body.token, body.new_password)
    except auth.AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/verify-email", response_model=UserPublic)
def verify_email(body: EmailVerifyConfirm, db: Session = Depends(get_db)) -> User:
    try:
        return auth.confirm_email_verification(db, body.token)
    except auth.AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/me", response_model=UserPublic)
def me(user: User = Depends(get_current_user)) -> User:
    return user
