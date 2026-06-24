"""Tests for video_localization_service.prepare_face_video — ffmpeg mocked."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.core.exceptions import VideoRenderError
from app.services import video_localization_service as vls


class _Proc:
    def __init__(self, returncode=0, stderr=""):
        self.returncode = returncode
        self.stderr = stderr


def test_prepare_face_video_success(settings, tmp_path, monkeypatch):
    def fake_run(cmd, **kw):
        Path(cmd[-1]).write_bytes(b"\x00" * 32)
        return _Proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    out = vls.prepare_face_video(tmp_path / "in.mp4", tmp_path / "out.mp4", settings)
    assert Path(out).exists()


def test_prepare_face_video_failure(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _Proc(1, "ffmpeg error"))
    with pytest.raises(VideoRenderError):
        vls.prepare_face_video(tmp_path / "in.mp4", tmp_path / "out.mp4", settings)


def test_prepare_face_video_applies_scale_and_fps(settings, tmp_path, monkeypatch):
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        Path(cmd[-1]).write_bytes(b"\x00")
        return _Proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    s = settings.model_copy(update={"lipsync_max_width": 320, "lipsync_fps": 24})
    vls.prepare_face_video(tmp_path / "in.mp4", tmp_path / "o.mp4", s)
    vf = captured["cmd"][captured["cmd"].index("-vf") + 1]
    assert "scale=320:-2" in vf and "fps=24" in vf
