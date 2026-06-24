"""Tests for lipsync_service — the Wav2Lip subprocess is faked."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.core.exceptions import ModelLoadError
from app.services import lipsync_service as ls


class _Proc:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def _setup_wav2lip(settings, tmp_path):
    """Create fake Wav2Lip dir + checkpoint so the availability check passes."""
    w = tmp_path / "Wav2Lip"
    (w / "checkpoints").mkdir(parents=True)
    (w / "inference.py").write_text("# fake", encoding="utf-8")
    (w / "checkpoints" / "wav2lip_gan.pth").write_bytes(b"\x00" * 16)
    return settings.model_copy(update={
        "wav2lip_dir": str(w),
        "wav2lip_checkpoint": str(w / "checkpoints" / "wav2lip_gan.pth"),
        "ffmpeg_path": "ffmpeg",
    })


def test_lipsync_missing_wav2lip_raises(settings, tmp_path):
    s = settings.model_copy(update={"wav2lip_dir": str(tmp_path / "nope"),
                                    "wav2lip_checkpoint": str(tmp_path / "nope.pth")})
    with pytest.raises(ModelLoadError):
        ls.lipsync(tmp_path / "f.mp4", tmp_path / "a.wav", tmp_path / "o.mp4", s)


def test_lipsync_success(settings, tmp_path, monkeypatch):
    s = _setup_wav2lip(settings, tmp_path)

    def fake_run(cmd, **kw):
        Path(cmd[cmd.index("--outfile") + 1]).write_bytes(b"\x00" * 64)
        return _Proc(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = ls.lipsync(tmp_path / "f.mp4", tmp_path / "a.wav", tmp_path / "out.mp4", s)
    assert Path(out).exists() and Path(out).stat().st_size > 0


def test_lipsync_failure_raises(settings, tmp_path, monkeypatch):
    s = _setup_wav2lip(settings, tmp_path)
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc(returncode=1, stdout="boom"))
    with pytest.raises(ls.LipSyncError):
        ls.lipsync(tmp_path / "f.mp4", tmp_path / "a.wav", tmp_path / "o.mp4", s)


def test_lipsync_env_includes_ffmpeg_dir(settings, tmp_path):
    s = settings.model_copy(update={"ffmpeg_path": str(tmp_path / "ff" / "ffmpeg.exe")})
    env = ls._env_with_ffmpeg(s)
    assert str(tmp_path / "ff") in env["PATH"]
