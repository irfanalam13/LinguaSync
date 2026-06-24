"""End-to-end flow: register → upload video → create job (eager worker) → result.

Uses the global temp DB + local storage + eager queue (see conftest). The Voice_ML HTTP
call is mocked so no real inference runs; the worker logic, storage, and DB updates are real.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("httpx")
pytest.importorskip("email_validator")
from fastapi.testclient import TestClient  # noqa: E402

from app.jobs import worker  # noqa: E402
from app.main import create_app  # noqa: E402
from shared.contracts import MLTranslateResponse, StageTimings  # noqa: E402


@pytest.fixture
def client():
    return TestClient(create_app())


def _auth(client, email):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _fake_ml(monkeypatch, similarity=0.61):
    """Mock the Voice_ML HTTP client; produce a real output file the worker can store."""
    out = Path(tempfile.mkdtemp(prefix="ml_out_")) / "final_output.mp4"
    out.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 256)

    class _FakeClient:
        def translate(self, req):
            return MLTranslateResponse(
                job_id=req.job_id or "j", source_language=req.source_language or "en",
                target_language=req.target_language, output_video=str(out),
                transcript_text="hi", translated_text="नमस्ते", artifacts_dir=str(out.parent),
                preserve_voice=req.preserve_voice or req.clone_voice or req.localize,
                similarity=similarity, timings=StageTimings(total=1.0),
            )

    monkeypatch.setattr(worker, "get_ml_client", lambda: _FakeClient())


def _upload(client, headers):
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 2048), "video/mp4")}
    r = client.post("/api/v1/videos/upload", files=files, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_full_flow_localize(client, monkeypatch):
    headers = _auth(client, "flow1@example.com")
    _fake_ml(monkeypatch, similarity=0.66)
    video_id = _upload(client, headers)

    r = client.post("/api/v1/jobs", json={"video_id": video_id, "target_language": "ne", "mode": "localize"}, headers=headers)
    assert r.status_code == 201, r.text
    job = r.json()
    # eager queue ran the worker inline → already completed
    assert job["status"] == "completed"
    assert job["similarity"] == 0.66
    assert job["result_key"] and job["progress"] == 100

    # download the result
    dl = client.get(f"/api/v1/jobs/{job['id']}/result", headers=headers)
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "video/mp4"
    assert len(dl.content) > 0


def test_upload_rejects_bad_type(client):
    headers = _auth(client, "flow2@example.com")
    files = {"file": ("x.txt", io.BytesIO(b"hello"), "text/plain")}
    r = client.post("/api/v1/videos/upload", files=files, headers=headers)
    assert r.status_code == 422


def test_job_requires_owned_video(client, monkeypatch):
    h1 = _auth(client, "owner@example.com")
    h2 = _auth(client, "other@example.com")
    _fake_ml(monkeypatch)
    vid = _upload(client, h1)
    # user2 cannot create a job on user1's video
    r = client.post("/api/v1/jobs", json={"video_id": vid, "target_language": "ne"}, headers=h2)
    assert r.status_code == 404


def test_usage_stats_after_job(client, monkeypatch):
    headers = _auth(client, "stats@example.com")
    _fake_ml(monkeypatch)
    vid = _upload(client, headers)
    client.post("/api/v1/jobs", json={"video_id": vid, "target_language": "ne"}, headers=headers)
    u = client.get("/api/v1/users/me/usage", headers=headers).json()
    assert u["videos"] >= 1 and u["jobs_total"] >= 1 and u["jobs_completed"] >= 1


def test_unauth_cannot_list(client):
    assert client.get("/api/v1/videos").status_code == 401
    assert client.get("/api/v1/jobs").status_code == 401
