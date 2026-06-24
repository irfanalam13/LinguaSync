"""Tests for transcription_service — the ASR backend is faked."""

from __future__ import annotations

import pytest

from app.core.exceptions import (
    CorruptAudioError,
    TranscriptionError,
    UnsupportedLanguageError,
)
from app.services import transcription_service as ts
from app.schemas.pipeline import TranscriptionResult


@pytest.fixture(autouse=True)
def reset_backend(monkeypatch):
    """Reset module singletons before each test."""
    monkeypatch.setattr(ts, "_FASTER_MODEL", None)
    monkeypatch.setattr(ts, "_WHISPER_MODEL", None)
    monkeypatch.setattr(ts, "_BACKEND", None)


def _install_fake_faster(monkeypatch, language="en"):
    class _Seg:
        def __init__(self, start, end, text):
            self.start, self.end, self.text = start, end, text

    class _Info:
        def __init__(self, lang):
            self.language = lang

    class _Model:
        def transcribe(self, *a, **k):
            return iter([_Seg(0.0, 1.0, "hello "), _Seg(1.0, 2.0, "world")]), _Info(language)

    monkeypatch.setattr(ts, "_BACKEND", "faster-whisper")
    monkeypatch.setattr(ts, "_FASTER_MODEL", _Model())
    monkeypatch.setattr(ts, "_load_model", lambda settings: None)


def test_transcribe_faster_backend(wav_factory, settings, tmp_path, monkeypatch):
    _install_fake_faster(monkeypatch, language="en")
    audio = wav_factory(tmp_path / "a.wav")
    result = ts.transcribe(audio, None, settings)
    assert isinstance(result, TranscriptionResult)
    assert result.language == "en"
    assert result.text == "hello world"
    assert len(result.segments) == 2
    assert result.segments[0].start == 0.0


def test_transcribe_missing_audio(settings):
    with pytest.raises(CorruptAudioError):
        ts.transcribe(settings.base_dir / "missing.wav", None, settings)


def test_transcribe_unsupported_forced_language(wav_factory, settings, tmp_path):
    audio = wav_factory(tmp_path / "a.wav")
    with pytest.raises(UnsupportedLanguageError):
        ts.transcribe(audio, "fr", settings)


def test_transcribe_unsupported_detected_language(wav_factory, settings, tmp_path, monkeypatch):
    _install_fake_faster(monkeypatch, language="fr")  # detect an unsupported lang
    audio = wav_factory(tmp_path / "a.wav")
    with pytest.raises(UnsupportedLanguageError):
        ts.transcribe(audio, None, settings)


def test_transcribe_wraps_backend_errors(wav_factory, settings, tmp_path, monkeypatch):
    class _Boom:
        def transcribe(self, *a, **k):
            raise RuntimeError("model exploded")

    monkeypatch.setattr(ts, "_BACKEND", "faster-whisper")
    monkeypatch.setattr(ts, "_FASTER_MODEL", _Boom())
    monkeypatch.setattr(ts, "_load_model", lambda settings: None)
    audio = wav_factory(tmp_path / "a.wav")
    with pytest.raises(TranscriptionError):
        ts.transcribe(audio, None, settings)
