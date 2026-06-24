"""Tests for speaker_profile_service — heavy extraction is mocked."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.exceptions import CorruptAudioError
from app.services import speaker_embedding_service as ses
from app.services import speaker_profile_service as sps
from app.services import voice_preservation_service as vps


def _wire(monkeypatch):
    monkeypatch.setattr(ses, "get_embedding", lambda a, s=None: np.ones(256, dtype=np.float32))
    monkeypatch.setattr(sps, "_segment_audio", lambda a, s: ["seg1.wav", "seg2.wav", "seg3.wav"])
    monkeypatch.setattr(vps, "extract_se_multi", lambda paths, s=None: np.ones(256, dtype=np.float32))
    monkeypatch.setattr(
        sps, "extract_acoustic_features",
        lambda a: {
            "duration_s": 30.0, "sample_rate": 16000,
            "pitch": {"mean_hz": 142.0, "median_hz": 138.0, "std_hz": 22.0},
            "energy": {"mean": 0.04, "std": 0.01},
            "speaking_rate_per_s": 3.2,
        },
    )


def test_build_profile_missing_sample(settings, tmp_path):
    with pytest.raises(CorruptAudioError):
        sps.build_profile(tmp_path / "nope.wav", settings=settings)


def test_build_profile_persists_files(settings, tmp_path, monkeypatch):
    _wire(monkeypatch)
    sample = tmp_path / "spk.wav"
    sample.write_bytes(b"RIFFxxxxWAVE")
    profile = sps.build_profile(sample, speaker_id="spk_test", settings=settings)

    out = Path(settings.speakers_dir) / "spk_test"
    assert (out / "profile.json").exists()
    assert (out / "embedding.npy").exists()
    assert (out / "se.pth").exists()
    assert profile["speaker_id"] == "spk_test"
    assert profile["num_reference_segments"] == 3
    assert profile["pitch"]["mean_hz"] == 142.0


def test_load_se_roundtrip(settings, tmp_path, monkeypatch):
    _wire(monkeypatch)
    sample = tmp_path / "spk.wav"
    sample.write_bytes(b"RIFFxxxxWAVE")
    profile = sps.build_profile(sample, speaker_id="spk_rt", settings=settings)
    se = sps.load_se(profile, settings)
    assert np.asarray(se).shape == (256,)
