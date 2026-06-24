"""Tests for the cloning pipeline (Phase 3) — all heavy steps mocked."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from app.pipelines import cloning_pipeline as cp
from app.schemas.pipeline import PipelineResult, StageTimings


def _write_wav(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)


@pytest.fixture
def base_artifacts(settings):
    art = settings.artifacts_dir / "job1"
    art.mkdir(parents=True, exist_ok=True)
    _write_wav(art / "audio.wav")
    _write_wav(art / "translated.wav")
    (art / "output.mp4").write_bytes(b"\x00" * 32)
    return PipelineResult(
        job_id="job1", source_language="en", target_language="ne",
        output_video=str(art / "output.mp4"), transcript_text="hi", translated_text="नमस्ते",
        artifacts_dir=str(art), timings=StageTimings(transcription=1.0, total=3.0),
    )


def _wire(monkeypatch, base_artifacts, base_sim=0.52, cloned_sim=0.78):
    monkeypatch.setattr(cp.translation_pipeline, "run_pipeline", lambda *a, **k: base_artifacts)
    monkeypatch.setattr(
        cp.speaker_profile_service, "build_profile",
        lambda sample, sid=None, s=None: {"speaker_id": "spk1", "num_reference_segments": 5},
    )

    def fake_clone(base, profile, out, s=None):
        _write_wav(Path(out))
        return str(out)

    monkeypatch.setattr(cp.voice_clone_service, "clone_to_profile", fake_clone)

    def fake_eval(ref, cand, s=None):
        sim = cloned_sim if "cloned" in str(cand) else base_sim
        return {"similarity": sim, "resemblyzer": sim, "speechbrain": None}

    monkeypatch.setattr(cp.quality_evaluation_service, "evaluate", fake_eval)
    monkeypatch.setattr(cp.video_service, "replace_audio", lambda v, a, o, s=None: str(o))


def test_cloning_pipeline_sets_similarity(settings, fake_video, monkeypatch, base_artifacts):
    _wire(monkeypatch, base_artifacts, base_sim=0.52, cloned_sim=0.81)
    result = cp.run_pipeline(fake_video, "ne", settings=settings)
    assert result.preserve_voice is True
    assert result.similarity == 0.81
    assert (Path(result.artifacts_dir) / "cloned.wav").exists()


def test_cloning_writes_quality_json(settings, fake_video, monkeypatch, base_artifacts):
    _wire(monkeypatch, base_artifacts, base_sim=0.50, cloned_sim=0.77)
    result = cp.run_pipeline(fake_video, "ne", settings=settings)
    qf = Path(result.artifacts_dir) / "cloning_quality.json"
    assert qf.exists()
    data = json.loads(qf.read_text(encoding="utf-8"))
    assert data["speaker_id"] == "spk1"
    assert data["cloned"]["similarity"] == 0.77
    assert data["improvement"] == pytest.approx(0.27, abs=1e-6)


def test_cloning_uses_separate_speaker_sample(settings, fake_video, monkeypatch, base_artifacts):
    captured = {}

    def capture_profile(sample, sid=None, s=None):
        captured["sample"] = str(sample)
        return {"speaker_id": "spk1", "num_reference_segments": 5}

    _wire(monkeypatch, base_artifacts)
    monkeypatch.setattr(cp.speaker_profile_service, "build_profile", capture_profile)
    enroll = settings.artifacts_dir / "enroll.wav"
    _write_wav(enroll)
    cp.run_pipeline(fake_video, "ne", settings=settings, speaker_sample=enroll)
    assert "enroll.wav" in captured["sample"]
