"""Tests for the localization pipeline (Phase 4) — all heavy steps mocked."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipelines import localization_pipeline as lp
from app.schemas.pipeline import PipelineResult, StageTimings


@pytest.fixture
def cloned_base(settings):
    art = settings.artifacts_dir / "job1"
    art.mkdir(parents=True, exist_ok=True)
    (art / "cloned.wav").write_bytes(b"RIFFxxxxWAVE")
    (art / "translated.wav").write_bytes(b"RIFFyyyyWAVE")
    (art / "output.mp4").write_bytes(b"\x00" * 32)
    return PipelineResult(
        job_id="job1", source_language="ne", target_language="en",
        output_video=str(art / "output.mp4"), transcript_text="x", translated_text="y",
        artifacts_dir=str(art), preserve_voice=True, similarity=0.67,
        timings=StageTimings(transcription=1.0, voice_conversion=2.0, total=5.0),
    )


def _wire(monkeypatch, cloned_base, face_present=True):
    monkeypatch.setattr(lp.cloning_pipeline, "run_pipeline", lambda *a, **k: cloned_base)
    monkeypatch.setattr(
        lp.video_localization_service, "prepare_face_video",
        lambda inp, out, s=None: (Path(out).write_bytes(b"\x00" * 16), str(out))[1],
    )
    monkeypatch.setattr(
        lp.face_detection_service, "detect_faces_in_video",
        lambda v, s=None: {"speaking_face_present": face_present, "frames_with_face": 5,
                           "frames_sampled": 5, "multiple_faces": False},
    )

    def fake_lipsync(face, audio, out, s=None):
        Path(out).write_bytes(b"\x00" * 128)
        return str(out)

    monkeypatch.setattr(lp.lipsync_service, "lipsync", fake_lipsync)


def test_localization_produces_final_output(settings, fake_video, monkeypatch, cloned_base):
    _wire(monkeypatch, cloned_base)
    result = lp.run_pipeline(fake_video, "en", settings=settings)
    art = Path(result.artifacts_dir)
    for name in ("original.mp4", "cloned.wav", "translated.wav", "lipsync.mp4", "final_output.mp4"):
        assert (art / name).exists(), f"missing artifact {name}"
    assert result.output_video.endswith("final_output.mp4")
    assert result.timings.lip_sync >= 0.0
    assert result.similarity == 0.67


def test_localization_no_face_raises(settings, fake_video, monkeypatch, cloned_base):
    _wire(monkeypatch, cloned_base, face_present=False)
    with pytest.raises(lp.FaceMissingError):
        lp.run_pipeline(fake_video, "en", settings=settings)


def test_localization_timings_accumulate(settings, fake_video, monkeypatch, cloned_base):
    _wire(monkeypatch, cloned_base)
    result = lp.run_pipeline(fake_video, "en", settings=settings)
    assert result.timings.total >= 5.0  # base total + lip_sync
