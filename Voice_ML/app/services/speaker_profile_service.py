"""Speaker profile extraction for voice cloning (Phase 3).

From a (≤30-s) speaker sample, builds and persists a speaker *profile* that captures
identity beyond Phase 2's single-reference timbre:

  - Resemblyzer d-vector embedding              → embedding.npy
  - OpenVoice **multi-reference** tone-color SE  → se.pth   (segments averaged)
  - pitch profile (F0 mean/median/std)           ┐
  - energy profile (RMS mean/std)                ├→ profile.json
  - speaking rate (onset rate) + duration        ┘

Persisted under ``storage/speakers/<speaker_id>/``. Heavy libs (librosa/torch) are
imported lazily so the global Phase 1 env (and mocked unit tests) are unaffected.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import CorruptAudioError, PipelineError
from app.core.logging import get_logger
from app.services import speaker_embedding_service, voice_preservation_service

log = get_logger("services.speaker_profile")


class SpeakerProfileError(PipelineError):
    """Raised when speaker-profile extraction fails."""


def _segment_audio(sample_audio: str | Path, settings: Settings) -> List[str]:
    """Split the sample into ~`clone_segment_seconds` chunks (capped to the sample
    window) written as temp WAVs for multi-reference SE extraction."""
    import librosa  # type: ignore
    import numpy as np  # type: ignore
    import scipy.io.wavfile  # type: ignore

    sr = 16000
    y, _ = librosa.load(str(sample_audio), sr=sr, mono=True)
    max_len = int(settings.clone_sample_seconds * sr)
    y = y[:max_len]
    seg_len = int(settings.clone_segment_seconds * sr)
    seg_dir = Path(settings.speaker_dir) / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)

    paths: List[str] = []
    for i in range(0, max(1, len(y)), seg_len):
        chunk = y[i : i + seg_len]
        if len(chunk) < sr * 0.5:  # skip <0.5s tails
            continue
        p = seg_dir / f"seg_{uuid.uuid4().hex[:8]}.wav"
        scipy.io.wavfile.write(str(p), sr, (np.clip(chunk, -1, 1) * 32767).astype(np.int16))
        paths.append(str(p))
    return paths or [str(sample_audio)]


def extract_acoustic_features(sample_audio: str | Path) -> Dict:
    """Pitch (F0), energy (RMS), speaking rate and duration via librosa."""
    import librosa  # type: ignore
    import numpy as np  # type: ignore

    y, sr = librosa.load(str(sample_audio), sr=16000, mono=True)
    duration = float(len(y) / sr) if sr else 0.0

    f0, _, _ = librosa.pyin(y, fmin=65, fmax=400, sr=sr)
    f0v = f0[~np.isnan(f0)] if f0 is not None else np.array([])
    pitch = {
        "mean_hz": round(float(np.mean(f0v)), 2) if f0v.size else 0.0,
        "median_hz": round(float(np.median(f0v)), 2) if f0v.size else 0.0,
        "std_hz": round(float(np.std(f0v)), 2) if f0v.size else 0.0,
    }
    rms = librosa.feature.rms(y=y)[0]
    energy = {"mean": round(float(np.mean(rms)), 5), "std": round(float(np.std(rms)), 5)}

    onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
    speaking_rate = round(len(onsets) / duration, 3) if duration else 0.0

    return {
        "duration_s": round(duration, 2),
        "sample_rate": sr,
        "pitch": pitch,
        "energy": energy,
        "speaking_rate_per_s": speaking_rate,
    }


def build_profile(
    sample_audio: str | Path,
    speaker_id: Optional[str] = None,
    settings: Settings | None = None,
) -> Dict:
    """Extract + persist a speaker profile; returns the profile dict."""
    settings = settings or get_settings()
    p = Path(sample_audio)
    if not p.exists() or p.stat().st_size == 0:
        raise CorruptAudioError(f"Speaker sample missing or empty: {p}")

    speaker_id = speaker_id or f"spk_{uuid.uuid4().hex[:10]}"
    out_dir = Path(settings.speakers_dir) / speaker_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import numpy as np  # type: ignore
        import torch  # type: ignore

        # 1) Resemblyzer d-vector.
        emb = speaker_embedding_service.get_embedding(sample_audio, settings)
        emb_path = out_dir / "embedding.npy"
        np.save(str(emb_path), emb)

        # 2) OpenVoice multi-reference tone-color SE.
        segments = _segment_audio(sample_audio, settings)
        se = voice_preservation_service.extract_se_multi(segments, settings)
        se_path = out_dir / "se.pth"
        torch.save(se.cpu() if hasattr(se, "cpu") else se, str(se_path))

        # 3) Acoustic features.
        feats = extract_acoustic_features(sample_audio)
    except PipelineError:
        raise
    except Exception as e:
        raise SpeakerProfileError(f"Speaker profile extraction failed: {e}") from e

    profile = {
        "speaker_id": speaker_id,
        "sample_audio": str(p),
        "num_reference_segments": len(segments),
        "embedding_path": str(emb_path),
        "se_path": str(se_path),
        "resemblyzer_dim": int(getattr(emb, "shape", [0])[0]) if hasattr(emb, "shape") else None,
        **feats,
    }
    (out_dir / "profile.json").write_text(json.dumps(profile, indent=2), encoding="utf-8")
    log.info("speaker profile built: %s (%d ref segments, %.1fs)",
             speaker_id, len(segments), feats.get("duration_s", 0.0))
    return profile


def load_se(profile: Dict, settings: Settings | None = None):
    """Load the persisted OpenVoice SE tensor from a profile dict."""
    import torch  # type: ignore

    return torch.load(profile["se_path"], map_location="cpu", weights_only=False)
