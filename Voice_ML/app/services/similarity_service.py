"""Speaker similarity scoring (cosine similarity of speaker embeddings).

Compares two audio files by their Resemblyzer speaker embeddings and returns a
similarity in [0, 1]. Used to (a) establish a baseline (source vs base TTS) and
(b) measure whether OpenVoice voice preservation improves on that baseline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services import speaker_embedding_service

log = get_logger("services.similarity")


def cosine_similarity(a, b) -> float:
    """Cosine similarity of two vectors, clamped to [0, 1]."""
    import numpy as np  # type: ignore

    a = np.asarray(a, dtype=np.float64).ravel()
    b = np.asarray(b, dtype=np.float64).ravel()
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
    sim = float(np.dot(a, b) / denom)
    # Embeddings can yield small negatives; clamp to a 0..1 similarity score.
    return max(0.0, min(1.0, sim))


def compare_audio(
    reference_audio: str | Path,
    candidate_audio: str | Path,
    settings: Settings | None = None,
) -> Dict[str, float]:
    """Return ``{"similarity": x}`` (0..1) between two audio files' speakers."""
    settings = settings or get_settings()
    ref_emb = speaker_embedding_service.get_embedding(reference_audio, settings)
    cand_emb = speaker_embedding_service.get_embedding(candidate_audio, settings)
    sim = round(cosine_similarity(ref_emb, cand_emb), 4)
    log.info("similarity: %.4f (%s vs %s)", sim, Path(reference_audio).name, Path(candidate_audio).name)
    return {"similarity": sim}
