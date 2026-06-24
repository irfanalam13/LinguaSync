"""Tests for voice_preservation_service — OpenVoice converter is faked."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from app.core.exceptions import ModelLoadError
from app.services import voice_preservation_service as vps


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(vps, "_CONVERTER", None)


def _write_wav(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 1600)


class _FakeConverter:
    def extract_se(self, wavs):
        return [[0.1] * 256]

    def convert(self, audio_src_path, src_se, tgt_se, output_path, message=""):
        _write_wav(Path(output_path))


def test_preserve_missing_checkpoint_raises(settings, tmp_path):
    s = settings.model_copy(update={"openvoice_ckpt": str(tmp_path / "no_ckpt")})
    with pytest.raises(ModelLoadError):
        vps.preserve_voice(tmp_path / "b.wav", tmp_path / "r.wav", tmp_path / "o.wav", s)


def test_preserve_voice_success(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(vps, "_load_converter", lambda s: _FakeConverter())
    base = tmp_path / "base.wav"
    ref = tmp_path / "ref.wav"
    _write_wav(base)
    _write_wav(ref)
    out = tmp_path / "preserved.wav"
    result = vps.preserve_voice(base, ref, out, settings)
    assert Path(result).exists() and Path(result).stat().st_size > 0


def test_extract_se_delegates(settings, monkeypatch):
    monkeypatch.setattr(vps, "_load_converter", lambda s: _FakeConverter())
    se = vps.extract_se("anything.wav", settings)
    assert len(se[0]) == 256
