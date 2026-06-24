"""Voice preservation via OpenVoice ToneColorConverter.

Transfers a *reference* speaker's timbre (the original video speaker) onto base-TTS
audio, so the translated speech sounds like the original speaker — without cloning
the content. Language-agnostic: works on Nepali or English base audio.

OpenVoice is loaded lazily (it lives only in the isolated Voice_ML/.venv); importing
this module costs nothing and the unit tests mock the converter, so the global Phase 1
env (no OpenVoice) is unaffected.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelLoadError, PipelineError
from app.core.logging import get_logger

log = get_logger("services.voice_preservation")

_CONVERTER = None


class VoicePreservationError(PipelineError):
    """Raised when tone-color conversion fails."""


def _load_converter(settings: Settings):
    global _CONVERTER
    if _CONVERTER is not None:
        return _CONVERTER
    ckpt_dir = Path(settings.openvoice_ckpt)
    config_path = ckpt_dir / "config.json"
    ckpt_path = ckpt_dir / "checkpoint.pth"
    if not config_path.exists() or not ckpt_path.exists():
        raise ModelLoadError(
            f"OpenVoice converter checkpoint not found in {ckpt_dir} "
            f"(need config.json + checkpoint.pth). See PHASE2_ENVIRONMENT.md."
        )
    try:
        from openvoice.api import ToneColorConverter  # type: ignore

        conv = ToneColorConverter(str(config_path), device=settings.resolved_device)
        conv.load_ckpt(str(ckpt_path))
        _CONVERTER = conv
        log.info("Voice preservation: OpenVoice ToneColorConverter (%s)", ckpt_dir)
        return _CONVERTER
    except ImportError as e:
        raise ModelLoadError("openvoice not installed in this env — required for voice preservation.") from e
    except Exception as e:  # pragma: no cover
        raise ModelLoadError(f"Failed to load OpenVoice converter: {e}") from e


def extract_se(audio_path: str | Path, settings: Settings | None = None):
    """Extract an OpenVoice speaker (tone-color) embedding from a single audio file."""
    return extract_se_multi([audio_path], settings)


def extract_se_multi(audio_paths, settings: Settings | None = None):
    """Multi-reference speaker embedding: average SE over several audio segments.

    OpenVoice's ``extract_se`` accepts a list and averages per-segment embeddings —
    used for Phase 3 identity cloning (richer voiceprint than a single reference).
    """
    settings = settings or get_settings()
    conv = _load_converter(settings)
    paths = [str(p) for p in audio_paths]
    if not paths:
        raise VoicePreservationError("extract_se_multi requires at least one audio path.")
    try:
        return conv.extract_se(paths)
    except Exception as e:
        raise VoicePreservationError(f"OpenVoice extract_se failed: {e}") from e


def convert_with_se(
    base_audio: str | Path,
    target_se,
    out_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Convert ``base_audio``'s timbre to a precomputed target speaker embedding.

    Unlike :func:`preserve_voice` (which extracts the target SE from a reference file),
    this takes an already-extracted (e.g. multi-reference) ``target_se`` — used for
    cloning from a stored speaker profile.
    """
    settings = settings or get_settings()
    conv = _load_converter(settings)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        base_se = conv.extract_se([str(base_audio)])
        conv.convert(
            audio_src_path=str(base_audio),
            src_se=base_se,
            tgt_se=target_se,
            output_path=str(out_path),
            message=settings.openvoice_message,
        )
    except Exception as e:
        raise VoicePreservationError(f"OpenVoice convert_with_se failed: {e}") from e
    if not Path(out_path).exists() or Path(out_path).stat().st_size == 0:
        raise VoicePreservationError(f"Voice cloning produced no audio at {out_path}")
    return str(out_path)


def preserve_voice(
    base_audio: str | Path,
    reference_audio: str | Path,
    out_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Convert ``base_audio``'s timbre to match ``reference_audio``'s speaker.

    Args:
        base_audio: base-TTS output (translated speech, generic voice).
        reference_audio: original speaker audio (the voice to preserve).
        out_path: where to write the speaker-preserved WAV.
    """
    settings = settings or get_settings()
    conv = _load_converter(settings)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    try:
        base_se = conv.extract_se([str(base_audio)])
        target_se = conv.extract_se([str(reference_audio)])
        conv.convert(
            audio_src_path=str(base_audio),
            src_se=base_se,
            tgt_se=target_se,
            output_path=str(out_path),
            message=settings.openvoice_message,
        )
    except Exception as e:
        raise VoicePreservationError(f"OpenVoice tone-color conversion failed: {e}") from e

    if not Path(out_path).exists() or Path(out_path).stat().st_size == 0:
        raise VoicePreservationError(f"Voice preservation produced no audio at {out_path}")
    return str(out_path)
