"""Tests for similarity_service — embeddings are injected directly."""

from __future__ import annotations

import numpy as np

from app.services import similarity_service as sim
from app.services import speaker_embedding_service as ses


def test_cosine_identical_is_one():
    v = np.array([1.0, 2.0, 3.0, 4.0])
    assert sim.cosine_similarity(v, v) == 1.0


def test_cosine_orthogonal_is_zero():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert sim.cosine_similarity(a, b) == 0.0


def test_cosine_opposite_clamped_to_zero():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert sim.cosine_similarity(a, b) == 0.0  # negative clamped


def test_compare_audio_returns_similarity_dict(settings, monkeypatch, tmp_path):
    # Two embeddings 45° apart -> cos = 1/sqrt(2) ≈ 0.7071
    embeds = {"ref": np.array([1.0, 0.0]), "cand": np.array([1.0, 1.0])}

    def fake_embed(path, settings=None):
        return embeds["ref"] if "ref" in str(path) else embeds["cand"]

    monkeypatch.setattr(ses, "get_embedding", fake_embed)
    (tmp_path / "ref.wav").write_bytes(b"x")
    (tmp_path / "cand.wav").write_bytes(b"x")
    out = sim.compare_audio(tmp_path / "ref.wav", tmp_path / "cand.wav", settings)
    assert "similarity" in out
    assert abs(out["similarity"] - 0.7071) < 1e-3
