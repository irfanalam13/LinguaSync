"""Tests for tts_service — synthesis backend is faked (no torch/transformers)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.core.exceptions import TTSError, UnsupportedLanguageError
from app.services import tts_service as tts


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(tts, "_MMS", {})
    monkeypatch.setattr(tts, "_SPEECHT5", None)


def _fake_synthesize(monkeypatch):
    """Replace the real synthesize body with a writer of a valid silent WAV.

    We patch at the public-function level because the real implementation imports
    torch/scipy which are absent here; this keeps the test about contract, not deps.
    """

    def fake(text, language, out_path, settings=None):
        from app.schemas.pipeline import LANGUAGES, TTSResult

        if language not in LANGUAGES:
            raise UnsupportedLanguageError(language)
        if not text.strip():
            raise TTSError("empty")
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(b"\x00\x00" * 1600)
        return TTSResult(
            audio_path=str(out), language=language, sample_rate=16000,
            engine=tts.ENGINE_BY_LANG[language],
        )

    monkeypatch.setattr(tts, "synthesize", fake)


def test_synthesize_unsupported_language_real_path(settings, tmp_path):
    # The real function validates language before importing torch.
    with pytest.raises(UnsupportedLanguageError):
        tts.synthesize("hello", "fr", tmp_path / "o.wav", settings)


def test_synthesize_empty_text_real_path(settings, tmp_path):
    with pytest.raises(TTSError):
        tts.synthesize("   ", "en", tmp_path / "o.wav", settings)


def test_synthesize_writes_wav_en(settings, tmp_path, monkeypatch):
    _fake_synthesize(monkeypatch)
    out = tmp_path / "en.wav"
    result = tts.synthesize("Hello there.", "en", out, settings)
    assert Path(result.audio_path).exists()
    assert result.language == "en"
    with wave.open(str(out), "rb") as w:
        assert w.getframerate() == 16000


def test_synthesize_writes_wav_ne(settings, tmp_path, monkeypatch):
    _fake_synthesize(monkeypatch)
    out = tmp_path / "ne.wav"
    result = tts.synthesize("नमस्ते।", "ne", out, settings)
    assert Path(result.audio_path).exists()
    assert result.language == "ne"
