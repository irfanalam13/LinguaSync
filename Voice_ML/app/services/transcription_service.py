"""Speech-to-text.

Primary backend: **faster-whisper** (CTranslate2 — fast, low memory).
Fallback:        **openai-whisper** (reference implementation).

The model is a lazy singleton: nothing is imported or downloaded until the first
``transcribe`` call, so importing this module is free and unit tests can run with
no ML stack installed. Supports English + Nepali, language auto-detection, and
timestamped segments.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.device import compute_type_for
from app.core.exceptions import (
    CorruptAudioError,
    ModelLoadError,
    TranscriptionError,
    UnsupportedLanguageError,
)
from app.core.logging import get_logger
from app.schemas.pipeline import LANGUAGES, SegmentSchema, TranscriptionResult

log = get_logger("services.transcription")

# Module-level singletons keyed by backend.
_FASTER_MODEL = None
_WHISPER_MODEL = None
_BACKEND: Optional[str] = None


def _load_model(settings: Settings):
    """Load the ASR model once, preferring faster-whisper, falling back to whisper."""
    global _FASTER_MODEL, _WHISPER_MODEL, _BACKEND
    if _BACKEND is not None:
        return

    device = settings.resolved_device
    # --- preferred: faster-whisper ---
    try:
        from faster_whisper import WhisperModel  # type: ignore

        _FASTER_MODEL = WhisperModel(
            settings.asr_model,
            device=device,
            compute_type=compute_type_for(device),
            download_root=str(settings.models_dir),
        )
        _BACKEND = "faster-whisper"
        log.info("ASR backend: faster-whisper (%s, %s)", settings.asr_model, device)
        return
    except ImportError:
        log.warning("faster-whisper unavailable; trying openai-whisper")
    except Exception as e:  # pragma: no cover - model/download failure
        log.warning("faster-whisper load failed (%s); trying openai-whisper", e)

    # --- fallback: openai-whisper ---
    try:
        import whisper  # type: ignore

        _WHISPER_MODEL = whisper.load_model(settings.asr_model, device=device)
        _BACKEND = "whisper"
        log.info("ASR backend: openai-whisper (%s, %s)", settings.asr_model, device)
    except Exception as e:
        raise ModelLoadError(
            "Could not load any ASR backend. Install 'faster-whisper' or 'openai-whisper'."
        ) from e


def _validate_audio(audio_path: str | Path) -> Path:
    p = Path(audio_path)
    if not p.exists() or p.stat().st_size == 0:
        raise CorruptAudioError(f"Audio file missing or empty: {p}")
    return p


def transcribe(
    audio_path: str | Path,
    language: Optional[str] = None,
    settings: Settings | None = None,
) -> TranscriptionResult:
    """Transcribe audio to text with timestamps.

    Args:
        audio_path: path to a WAV/audio file.
        language: optional ISO-639-1 code ("en"/"ne") to force; ``None`` = auto-detect.
    """
    settings = settings or get_settings()
    p = _validate_audio(audio_path)

    if language is not None and language not in LANGUAGES:
        raise UnsupportedLanguageError(
            f"Unsupported source language '{language}'. Supported: {list(LANGUAGES)}"
        )

    _load_model(settings)

    try:
        if _BACKEND == "faster-whisper":
            return _transcribe_faster(p, language, settings)
        return _transcribe_whisper(p, language, settings)
    except (CorruptAudioError, UnsupportedLanguageError):
        raise
    except Exception as e:
        raise TranscriptionError(f"Transcription failed: {e}") from e


def _transcribe_faster(p: Path, language: Optional[str], settings: Settings) -> TranscriptionResult:
    segments_iter, info = _FASTER_MODEL.transcribe(  # type: ignore[union-attr]
        str(p),
        language=language,
        beam_size=settings.asr_beam_size,
        vad_filter=True,
    )
    segments = [
        SegmentSchema(start=round(s.start, 3), end=round(s.end, 3), text=s.text.strip())
        for s in segments_iter
    ]
    text = " ".join(s.text for s in segments).strip()
    detected = getattr(info, "language", language) or "en"
    return _finalize(detected, text, segments)


def _transcribe_whisper(p: Path, language: Optional[str], settings: Settings) -> TranscriptionResult:
    result = _WHISPER_MODEL.transcribe(str(p), language=language)  # type: ignore[union-attr]
    segments = [
        SegmentSchema(
            start=round(float(s["start"]), 3),
            end=round(float(s["end"]), 3),
            text=str(s["text"]).strip(),
        )
        for s in result.get("segments", [])
    ]
    text = str(result.get("text", "")).strip()
    detected = result.get("language", language) or "en"
    return _finalize(detected, text, segments)


def _finalize(detected: str, text: str, segments) -> TranscriptionResult:
    if detected not in LANGUAGES:
        # We can still transcribe an unexpected language, but Phase 1 only
        # translates en<->ne, so flag it early with a clear message.
        raise UnsupportedLanguageError(
            f"Detected language '{detected}' is not supported in Phase 1 (en, ne only)."
        )
    return TranscriptionResult(language=detected, text=text, segments=segments)
