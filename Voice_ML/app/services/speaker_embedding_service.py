"""Speaker embedding extraction (Resemblyzer).

Extracts a fixed-length speaker embedding (d-vector) capturing voice timbre/identity
from an audio file. Used (a) as a baseline similarity reference and (b) — with
OpenVoice — as the target timbre for voice preservation.

The Resemblyzer ``VoiceEncoder`` is a lazy singleton: importing this module costs
nothing and unit tests mock the encoder, so the global Phase 1 env (without
resemblyzer) is unaffected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import CorruptAudioError, ModelLoadError, PipelineError
from app.core.logging import get_logger

log = get_logger("services.speaker_embedding")

_ENCODER = None


class SpeakerEmbeddingError(PipelineError):
    """Raised when speaker-embedding extraction fails."""


def _load_encoder(settings: Settings):
    global _ENCODER
    if _ENCODER is not None:
        return _ENCODER
    try:
        from resemblyzer import VoiceEncoder  # type: ignore

        device = "cuda" if settings.resolved_device == "cuda" else "cpu"
        _ENCODER = VoiceEncoder(device=device)
        log.info("Speaker encoder: Resemblyzer VoiceEncoder (%s)", device)
        return _ENCODER
    except ImportError as e:
        raise ModelLoadError("resemblyzer not installed — required for speaker embeddings.") from e
    except Exception as e:  # pragma: no cover
        raise ModelLoadError(f"Failed to load Resemblyzer VoiceEncoder: {e}") from e


def get_embedding(audio_path: str | Path, settings: Settings | None = None):
    """Return a 256-d speaker embedding (numpy array) for ``audio_path``."""
    settings = settings or get_settings()
    p = Path(audio_path)
    if not p.exists() or p.stat().st_size == 0:
        raise CorruptAudioError(f"Audio file missing or empty: {p}")

    encoder = _load_encoder(settings)
    try:
        from resemblyzer import preprocess_wav  # type: ignore

        wav = preprocess_wav(str(p))
        return encoder.embed_utterance(wav)
    except Exception as e:
        raise SpeakerEmbeddingError(f"Speaker embedding extraction failed: {e}") from e


def save_embedding(embedding, job_id: str, settings: Settings | None = None) -> str:
    """Persist an embedding under ``temp/speaker/<job_id>.npy`` and return its path."""
    settings = settings or get_settings()
    import numpy as np  # type: ignore

    settings.ensure_dirs()
    out = Path(settings.speaker_dir) / f"{job_id}.npy"
    np.save(str(out), embedding)
    return str(out)
