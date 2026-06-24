"""Auth API tests — isolated in-memory SQLite via dependency override."""

from __future__ import annotations

import pytest

pytest.importorskip("httpx")
pytest.importorskip("email_validator")
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import security  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _register(client, email="u@example.com", pw="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": pw, "full_name": "U"})


def test_register_and_me(client):
    r = _register(client)
    assert r.status_code == 201
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == "u@example.com"
    assert me.json()["is_verified"] is False


def test_register_duplicate_409(client):
    _register(client)
    assert _register(client).status_code == 409


def test_login_wrong_password_401(client):
    _register(client)
    r = client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_refresh_rotates_and_revokes_old(client):
    tokens = _register(client).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != tokens["refresh_token"]
    # old refresh token is now revoked
    again = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert again.status_code == 401


def test_logout_revokes_refresh(client):
    tokens = _register(client).json()
    assert client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_password_reset_flow(client):
    _register(client, pw="oldpassword1")
    req = client.post("/api/v1/auth/password-reset/request", json={"email": "u@example.com"})
    token = req.json()["reset_token"]
    assert token
    assert client.post("/api/v1/auth/password-reset/confirm",
                       json={"token": token, "new_password": "newpassword1"}).status_code == 204
    # old password fails, new works
    assert client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "oldpassword1"}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "newpassword1"}).status_code == 200


def test_password_reset_unknown_email_no_leak(client):
    r = client.post("/api/v1/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert r.status_code == 200 and r.json()["reset_token"] is None


def test_email_verification(client):
    tokens = _register(client).json()
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).json()
    verify_token = security.create_purpose_token(me["id"], security.VERIFY)
    r = client.post("/api/v1/auth/verify-email", json={"token": verify_token})
    assert r.status_code == 200 and r.json()["is_verified"] is True
