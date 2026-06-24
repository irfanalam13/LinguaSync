"""Tests for quality_evaluation_service — Resemblyzer + optional SpeechBrain."""

from __future__ import annotations

import pytest

from app.services import quality_evaluation_service as qes
from app.services import similarity_service


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(qes, "_ECAPA", None)
    monkeypatch.setattr(qes, "_ECAPA_FAILED", False)


def test_evaluate_resemblyzer_only(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_service, "compare_audio", lambda r, c, s=None: {"similarity": 0.70})
    monkeypatch.setattr(qes, "_speechbrain_similarity", lambda r, c, s: None)  # SB unavailable
    out = qes.evaluate(tmp_path / "ref.wav", tmp_path / "cand.wav", settings)
    assert out["resemblyzer"] == 0.70
    assert out["speechbrain"] is None
    assert out["similarity"] == 0.70  # mean of available = resemblyzer only


def test_evaluate_dual_metric_mean(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_service, "compare_audio", lambda r, c, s=None: {"similarity": 0.70})
    monkeypatch.setattr(qes, "_speechbrain_similarity", lambda r, c, s: 0.80)
    out = qes.evaluate(tmp_path / "ref.wav", tmp_path / "cand.wav", settings)
    assert out["resemblyzer"] == 0.70
    assert out["speechbrain"] == 0.80
    assert out["similarity"] == 0.75  # mean(0.70, 0.80)


def test_evaluate_speechbrain_failure_falls_back(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(similarity_service, "compare_audio", lambda r, c, s=None: {"similarity": 0.66})
    # Simulate SpeechBrain import/runtime failure inside the real helper.
    monkeypatch.setattr(qes, "_ECAPA_FAILED", True)
    out = qes.evaluate(tmp_path / "ref.wav", tmp_path / "cand.wav", settings)
    assert out["speechbrain"] is None
    assert out["similarity"] == 0.66
