"""Tests for the speaker-preservation pipeline (Phase 2) — all heavy steps mocked."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.pipelines import speaker_preservation_pipeline as spp
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
    """Simulate the base pipeline: create artifacts and return a PipelineResult."""
    art = settings.artifacts_dir / "job1"
    art.mkdir(parents=True, exist_ok=True)
    _write_wav(art / "audio.wav")
    _write_wav(art / "translated.wav")
    (art / "output.mp4").write_bytes(b"\x00" * 32)
    return PipelineResult(
        job_id="job1",
        source_language="en",
        target_language="ne",
        output_video=str(art / "output.mp4"),
        transcript_text="hello",
        translated_text="नमस्ते",
        artifacts_dir=str(art),
        timings=StageTimings(transcription=1.0, translation=1.0, tts=1.0, total=3.0),
    )


def _wire(monkeypatch, base_artifacts, sim_before=0.50, sim_after=0.72):
    monkeypatch.setattr(spp.translation_pipeline, "run_pipeline", lambda *a, **k: base_artifacts)

    def fake_preserve(base_audio, ref_audio, out_path, settings=None):
        _write_wav(Path(out_path))
        return str(out_path)

    monkeypatch.setattr(spp.voice_preservation_service, "preserve_voice", fake_preserve)

    calls = {"n": 0}

    def fake_compare(ref, cand, settings=None):
        # first call = baseline (vs translated.wav), second = preserved
        calls["n"] += 1
        return {"similarity": sim_before if "translated" in str(cand) else sim_after}

    monkeypatch.setattr(spp.similarity_service, "compare_audio", fake_compare)
    monkeypatch.setattr(spp.video_service, "replace_audio", lambda v, a, o, s=None: str(o))


def test_preservation_pipeline_sets_similarity(settings, fake_video, monkeypatch, base_artifacts):
    _wire(monkeypatch, base_artifacts, sim_before=0.50, sim_after=0.72)
    result = spp.run_pipeline(fake_video, "ne", settings=settings)
    assert result.preserve_voice is True
    assert result.similarity == 0.72
    assert result.timings.voice_conversion >= 0.0
    assert result.timings.total >= 3.0


def test_preservation_writes_similarity_json(settings, fake_video, monkeypatch, base_artifacts):
    _wire(monkeypatch, base_artifacts, sim_before=0.48, sim_after=0.66)
    result = spp.run_pipeline(fake_video, "ne", settings=settings)
    sim_file = Path(result.artifacts_dir) / "similarity.json"
    assert sim_file.exists()
    import json

    data = json.loads(sim_file.read_text(encoding="utf-8"))
    assert data["baseline_similarity"] == 0.48
    assert data["preserved_similarity"] == 0.66
    assert data["improvement"] == pytest.approx(0.18, abs=1e-6)


def test_preservation_produces_preserved_wav(settings, fake_video, monkeypatch, base_artifacts):
    _wire(monkeypatch, base_artifacts)
    result = spp.run_pipeline(fake_video, "ne", settings=settings)
    assert (Path(result.artifacts_dir) / "preserved.wav").exists()
