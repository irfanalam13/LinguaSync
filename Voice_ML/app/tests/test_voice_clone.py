"""Tests for voice_clone_service — OpenVoice convert is mocked."""

from __future__ import annotations

import wave
from pathlib import Path

from app.services import speaker_profile_service as sps
from app.services import voice_clone_service as vcs
from app.services import voice_preservation_service as vps


def _write_wav(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)


def test_clone_to_profile(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(sps, "load_se", lambda profile, s=None: [[0.2] * 256])

    def fake_convert(base, target_se, out, s=None):
        _write_wav(Path(out))
        return str(out)

    monkeypatch.setattr(vps, "convert_with_se", fake_convert)

    base = tmp_path / "base.wav"
    _write_wav(base)
    out = tmp_path / "cloned.wav"
    profile = {"speaker_id": "spk1", "se_path": "x"}
    result = vcs.clone_to_profile(base, profile, out, settings)
    assert Path(result).exists() and Path(result).stat().st_size > 0


def test_clone_uses_profile_se(settings, tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(sps, "load_se", lambda profile, s=None: "SE_OBJECT")

    def fake_convert(base, target_se, out, s=None):
        captured["se"] = target_se
        Path(out).write_bytes(b"x")
        return str(out)

    monkeypatch.setattr(vps, "convert_with_se", fake_convert)
    vcs.clone_to_profile(tmp_path / "b.wav", {"speaker_id": "s", "se_path": "x"}, tmp_path / "o.wav", settings)
    assert captured["se"] == "SE_OBJECT"
