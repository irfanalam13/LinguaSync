"""End-to-end pipeline tests with every service mocked.

Verifies the orchestration contract: artifacts are written, timings recorded,
both directions work, and failure modes propagate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import InvalidVideoError, UnsupportedLanguageError
from app.schemas.pipeline import (
    TranscriptionResult,
    TranslationResult,
    TTSResult,
    SegmentSchema,
)
from app.pipelines import translation_pipeline as pl


def _mock_services(monkeypatch, detected_lang="en", target="ne"):
    vs = pl.video_service
    monkeypatch.setattr(vs, "validate_video", lambda v, s=None: None)

    def fake_extract(video, audio_path, settings=None):
        Path(audio_path).write_bytes(b"RIFFxxxxWAVE")
        return str(audio_path)

    monkeypatch.setattr(vs, "extract_audio", fake_extract)

    def fake_replace(video, audio, out, settings=None):
        Path(out).write_bytes(b"\x00" * 32)
        return str(out)

    monkeypatch.setattr(vs, "replace_audio", fake_replace)

    monkeypatch.setattr(
        pl.transcription_service, "transcribe",
        lambda audio, src, settings=None: TranscriptionResult(
            language=detected_lang,
            text="hello world",
            segments=[SegmentSchema(start=0.0, end=1.0, text="hello world")],
        ),
    )
    monkeypatch.setattr(
        pl.translation_service, "translate",
        lambda text, src, tgt, settings=None: TranslationResult(
            source_language=src, target_language=tgt, translated_text="translated text"
        ),
    )

    def fake_tts(text, language, out_path, settings=None):
        Path(out_path).write_bytes(b"RIFFyyyyWAVE")
        return TTSResult(audio_path=str(out_path), language=language, sample_rate=16000, engine="fake")

    monkeypatch.setattr(pl.tts_service, "synthesize", fake_tts)


def test_pipeline_en_to_ne(settings, fake_video, monkeypatch):
    _mock_services(monkeypatch, detected_lang="en", target="ne")
    result = pl.run_pipeline(fake_video, "ne", settings=settings)

    assert result.source_language == "en"
    assert result.target_language == "ne"
    art = Path(result.artifacts_dir)
    for name in ("audio.wav", "transcript.txt", "translated.txt", "translated.wav", "output.mp4"):
        assert (art / name).exists(), f"missing artifact {name}"
    assert (art / "transcript.txt").read_text(encoding="utf-8") == "hello world"
    assert (art / "translated.txt").read_text(encoding="utf-8") == "translated text"
    assert result.timings.total >= 0.0


def test_pipeline_ne_to_en(settings, fake_video, monkeypatch):
    _mock_services(monkeypatch, detected_lang="ne", target="en")
    result = pl.run_pipeline(fake_video, "en", settings=settings)
    assert result.source_language == "ne"
    assert result.target_language == "en"
    assert Path(result.output_video).exists()


def test_pipeline_progress_callback(settings, fake_video, monkeypatch):
    _mock_services(monkeypatch)
    seen: list[str] = []
    pl.run_pipeline(fake_video, "ne", settings=settings, progress=seen.append)
    assert "done" in seen
    assert any("transcribing" in m for m in seen)


def test_pipeline_rejects_bad_target(settings, fake_video):
    with pytest.raises(UnsupportedLanguageError):
        pl.run_pipeline(fake_video, "fr", settings=settings)


def test_pipeline_rejects_same_source_target(settings, fake_video, monkeypatch):
    _mock_services(monkeypatch, detected_lang="ne", target="ne")
    with pytest.raises(UnsupportedLanguageError):
        pl.run_pipeline(fake_video, "ne", settings=settings)


def test_pipeline_propagates_invalid_video(settings, fake_video, monkeypatch):
    def bad_validate(v, s=None):
        raise InvalidVideoError("nope")

    monkeypatch.setattr(pl.video_service, "validate_video", bad_validate)
    with pytest.raises(InvalidVideoError):
        pl.run_pipeline(fake_video, "ne", settings=settings)


def test_pipeline_uses_given_job_id(settings, fake_video, monkeypatch):
    _mock_services(monkeypatch)
    result = pl.run_pipeline(fake_video, "ne", job_id="fixedjob123", settings=settings)
    assert result.job_id == "fixedjob123"
    assert result.artifacts_dir.endswith("fixedjob123")
