"""Tests for speaker_embedding_service — Resemblyzer is faked (no ML stack needed)."""

from __future__ import annotations

import sys
import types

import numpy as np
import pytest

from app.core.exceptions import CorruptAudioError
from app.services import speaker_embedding_service as ses


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(ses, "_ENCODER", None)


def _install_fake_resemblyzer(monkeypatch, vector=None):
    """Inject a fake `resemblyzer` module so get_embedding runs without the real one."""
    vector = vector if vector is not None else np.ones(256, dtype=np.float32)

    fake = types.ModuleType("resemblyzer")

    class _Encoder:
        def __init__(self, device="cpu"):
            self.device = device

        def embed_utterance(self, wav):
            return vector

    fake.VoiceEncoder = _Encoder
    fake.preprocess_wav = lambda path: np.zeros(16000, dtype=np.float32)
    monkeypatch.setitem(sys.modules, "resemblyzer", fake)


def test_get_embedding_missing_file(settings):
    with pytest.raises(CorruptAudioError):
        ses.get_embedding(settings.base_dir / "nope.wav", settings)


def test_get_embedding_success(wav_factory, tmp_path, settings, monkeypatch):
    _install_fake_resemblyzer(monkeypatch, vector=np.arange(256, dtype=np.float32))
    audio = wav_factory(tmp_path / "a.wav")
    emb = ses.get_embedding(audio, settings)
    assert emb.shape == (256,)
    assert emb[1] == 1.0


def test_save_embedding(settings, tmp_path):
    emb = np.ones(256, dtype=np.float32)
    path = ses.save_embedding(emb, "job42", settings)
    assert path.endswith("job42.npy")
    loaded = np.load(path)
    assert loaded.shape == (256,)
