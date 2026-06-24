"""Voice-cloning quality scoring (Phase 3).

Combines two independent speaker-verification metrics:
  - **Resemblyzer** d-vector cosine (always available)
  - **SpeechBrain** ECAPA-TDNN cosine (spkrec-ecapa-voxceleb) — optional; if unavailable
    the score falls back to Resemblyzer-only (recorded honestly, never faked).

Returns ``{"similarity": x, "resemblyzer": r, "speechbrain": s|None}`` where ``similarity``
is the mean of the available metrics. Models are lazy; the global env / mocked tests are
unaffected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services import similarity_service

log = get_logger("services.quality_evaluation")

_ECAPA = None
_ECAPA_FAILED = False


def _speechbrain_similarity(reference_audio, candidate_audio, settings: Settings) -> Optional[float]:
    """ECAPA cosine similarity, or None if SpeechBrain isn't usable here."""
    global _ECAPA, _ECAPA_FAILED
    if _ECAPA_FAILED:
        return None
    try:
        import torch  # type: ignore

        if _ECAPA is None:
            from speechbrain.inference import EncoderClassifier  # type: ignore

            kwargs = {
                "source": "speechbrain/spkrec-ecapa-voxceleb",
                "savedir": str(Path(settings.models_dir) / "ecapa"),
                "run_opts": {"device": settings.resolved_device},
            }
            # Windows without Developer Mode can't symlink (WinError 1314); force copy.
            try:
                from speechbrain.utils.fetching import LocalStrategy  # type: ignore

                kwargs["local_strategy"] = LocalStrategy.COPY_SKIP_CACHE
            except Exception:
                pass
            _ECAPA = EncoderClassifier.from_hparams(**kwargs)

        def _emb(path):
            # Load via soundfile/librosa to avoid torchaudio's TorchCodec backend.
            import librosa  # type: ignore
            import soundfile as sf  # type: ignore

            data, sr = sf.read(str(path), dtype="float32")
            if getattr(data, "ndim", 1) > 1:
                data = data.mean(axis=1)
            if sr != 16000:
                data = librosa.resample(data, orig_sr=sr, target_sr=16000)
            sig = torch.tensor(data).unsqueeze(0)  # (1, n)
            return _ECAPA.encode_batch(sig).squeeze()

        ref, cand = _emb(reference_audio), _emb(candidate_audio)
        cos = torch.nn.functional.cosine_similarity(ref, cand, dim=0).item()
        return max(0.0, min(1.0, float(cos)))
    except Exception as e:  # pragma: no cover - optional path
        log.warning("SpeechBrain ECAPA unavailable (%s); using Resemblyzer only.", e)
        _ECAPA_FAILED = True
        return None


def evaluate(
    reference_audio: str | Path,
    candidate_audio: str | Path,
    settings: Settings | None = None,
) -> Dict[str, Optional[float]]:
    """Score how well ``candidate_audio`` matches ``reference_audio``'s speaker."""
    settings = settings or get_settings()
    resemblyzer = similarity_service.compare_audio(reference_audio, candidate_audio, settings)["similarity"]
    speechbrain = _speechbrain_similarity(reference_audio, candidate_audio, settings)

    metrics = [m for m in (resemblyzer, speechbrain) if m is not None]
    similarity = round(sum(metrics) / len(metrics), 4) if metrics else 0.0
    result = {
        "similarity": similarity,
        "resemblyzer": round(resemblyzer, 4),
        "speechbrain": round(speechbrain, 4) if speechbrain is not None else None,
    }
    log.info("quality: %s", result)
    return result
