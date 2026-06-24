"""API gateway tests — the Voice_ML service is mocked (no real inference)."""

from __future__ import annotations

import io

import pytest

pytest.importorskip("httpx", reason="httpx required for FastAPI TestClient")
from fastapi.testclient import TestClient  # noqa: E402

from app.api import routes  # noqa: E402
from app.jobs.ml_client import MLServiceError  # noqa: E402
from app.main import create_app  # noqa: E402
from shared.contracts import MLTranslateResponse, StageTimings  # noqa: E402


class _FakeMLClient:
    def __init__(self, response=None, error=None):
        self._response, self._error = response, error

    def health(self):
        return {"status": "ok", "service": "voice_ml"}

    def translate(self, req):
        if self._error:
            raise self._error
        return self._response


def _fake_response(job_id="job123", target="ne", source="en", preserve=False, sim=None):
    return MLTranslateResponse(
        job_id=job_id,
        source_language=source,
        target_language=target,
        output_video=f"/artifacts/{job_id}/output.mp4",
        transcript_text="hi",
        translated_text="नमस्ते",
        artifacts_dir=f"/artifacts/{job_id}",
        preserve_voice=preserve,
        similarity=sim,
        timings=StageTimings(total=2.0),
    )


@pytest.fixture
def client(settings, monkeypatch):
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    return TestClient(create_app())


def _install_client(monkeypatch, fake):
    monkeypatch.setattr(routes, "get_ml_client", lambda: fake)


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["service"] == "voice_backend"


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200 and r.json()["name"] == "voice-backend"


def test_translate_success(client, monkeypatch):
    _install_client(monkeypatch, _FakeMLClient(response=_fake_response()))
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 128), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "ne"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["output_video"].endswith("output.mp4")
    assert body["target_language"] == "ne"


def test_translate_preserve_voice_flag_forwarded(client, monkeypatch):
    captured = {}

    class _Capt(_FakeMLClient):
        def translate(self, req):
            captured["preserve"] = req.preserve_voice
            return _fake_response(preserve=req.preserve_voice, sim=0.81)

    _install_client(monkeypatch, _Capt())
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 128), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "ne", "preserve_voice": "true"})
    assert r.status_code == 200
    assert captured["preserve"] is True
    assert r.json()["similarity"] == 0.81


def test_translate_bad_target(client):
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 128), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "fr"})
    assert r.status_code == 422


def test_translate_empty_upload(client):
    files = {"file": ("clip.mp4", io.BytesIO(b""), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "ne"})
    assert r.status_code == 422


def test_translate_ml_unavailable_returns_502(client, monkeypatch):
    _install_client(monkeypatch, _FakeMLClient(error=MLServiceError("ML down")))
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 128), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "ne"})
    assert r.status_code == 502


def test_legacy_translate_still_works(client, monkeypatch):
    # The legacy direct-HTTP /translate route remains (Phase 2); the legacy in-memory
    # job-status route was removed in Phase 5 (superseded by the authenticated jobs API).
    _install_client(monkeypatch, _FakeMLClient(response=_fake_response(job_id="trackme")))
    files = {"file": ("clip.mp4", io.BytesIO(b"\x00" * 128), "video/mp4")}
    r = client.post("/api/v1/translate", files=files, data={"target": "ne"})
    assert r.status_code == 200 and r.json()["status"] == "completed"
