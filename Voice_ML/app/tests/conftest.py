"""Shared pytest fixtures.

The whole suite runs WITHOUT the heavy ML stack (torch/whisper/transformers/TTS)
and WITHOUT ffmpeg installed: every external dependency is mocked. This keeps the
tests fast, deterministic, and runnable in CI on a plain machine. Real end-to-end
runs with actual models are exercised manually (see TEST_REPORT.md).
"""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.core.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """A Settings instance with all directories redirected into a tmp dir."""
    s = Settings(
        base_dir=tmp_path,
        artifacts_dir=tmp_path / "artifacts",
        uploads_dir=tmp_path / "uploads",
        logs_dir=tmp_path / "logs",
        models_dir=tmp_path / "models",
        speaker_dir=tmp_path / "temp" / "speaker",
        speakers_dir=tmp_path / "storage" / "speakers",
        device="cpu",
    )
    s.ensure_dirs()
    return s


@pytest.fixture
def fake_video(tmp_path: Path) -> Path:
    """A non-empty placeholder 'video' file (content is irrelevant — ffmpeg is mocked)."""
    p = tmp_path / "input.mp4"
    p.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64)
    return p


def _write_wav(path: Path, seconds: float = 0.2, rate: int = 16000) -> Path:
    """Write a tiny silent mono WAV so 'audio' files are real and non-empty."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * n)
    return path


@pytest.fixture
def wav_factory():
    """Factory to create small valid WAV files on demand."""
    return _write_wav
