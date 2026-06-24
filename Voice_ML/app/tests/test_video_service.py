"""Tests for video_service — ffmpeg is mocked via subprocess.run."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from app.core.exceptions import (
    AudioExtractionError,
    FFmpegNotFoundError,
    InvalidVideoError,
    VideoRenderError,
)
from app.services import video_service


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_validate_video_missing(settings):
    with pytest.raises(InvalidVideoError):
        video_service.validate_video(settings.base_dir / "nope.mp4", settings)


def test_validate_video_empty(tmp_path, settings):
    # Size check fires before the ffmpeg check, so no ffmpeg needed here.
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    with pytest.raises(InvalidVideoError):
        video_service.validate_video(empty, settings)


def test_validate_video_no_ffmpeg(fake_video, settings, monkeypatch):
    import app.core.config as config_mod

    monkeypatch.setattr(config_mod.shutil, "which", lambda _name: None)
    with pytest.raises(FFmpegNotFoundError):
        video_service.validate_video(fake_video, settings)


def test_extract_audio_success(fake_video, settings, monkeypatch):
    audio_out = settings.artifacts_dir / "audio.wav"

    def fake_run(cmd, **kw):
        # Simulate ffmpeg producing the output file.
        Path(cmd[-1]).write_bytes(b"RIFFxxxxWAVE")
        return _Proc(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = video_service.extract_audio(fake_video, audio_out, settings)
    assert Path(out).exists() and Path(out).stat().st_size > 0


def test_extract_audio_ffmpeg_failure(fake_video, settings, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc(returncode=1, stderr="boom"))
    with pytest.raises(AudioExtractionError):
        video_service.extract_audio(fake_video, settings.artifacts_dir / "a.wav", settings)


def test_extract_audio_binary_missing(fake_video, settings, monkeypatch):
    def raise_fnf(cmd, **kw):
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(subprocess, "run", raise_fnf)
    with pytest.raises(FFmpegNotFoundError):
        video_service.extract_audio(fake_video, settings.artifacts_dir / "a.wav", settings)


def test_replace_audio_success(fake_video, settings, monkeypatch):
    audio = settings.artifacts_dir / "voice.wav"
    audio.write_bytes(b"RIFFxxxxWAVE")
    out = settings.artifacts_dir / "out.mp4"

    def fake_run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"\x00" * 32)
        return _Proc(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = video_service.replace_audio(fake_video, audio, out, settings)
    assert Path(result).exists()


def test_replace_audio_failure(fake_video, settings, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc(returncode=1, stderr="x"))
    with pytest.raises(VideoRenderError):
        video_service.replace_audio(fake_video, fake_video, settings.artifacts_dir / "o.mp4", settings)


def test_get_video_metadata(fake_video, settings, monkeypatch):
    probe = {
        "format": {"duration": "12.5"},
        "streams": [
            {"codec_type": "video", "width": 1280, "height": 720, "codec_name": "h264"},
            {"codec_type": "audio"},
        ],
    }
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc(0, json.dumps(probe)))
    meta = video_service.get_video_metadata(fake_video, settings)
    assert meta.duration == 12.5
    assert meta.width == 1280 and meta.height == 720
    assert meta.has_audio is True
    assert meta.codec == "h264"


def test_merge_video_audio_alias(fake_video, settings, monkeypatch):
    monkeypatch.setattr(
        video_service, "replace_audio", lambda *a, **k: "ALIASED"
    )
    assert video_service.merge_video_audio(fake_video, fake_video, "x.mp4", settings) == "ALIASED"
