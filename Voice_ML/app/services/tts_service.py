"""Text-to-speech (offline, English + Nepali) — engine-agnostic, per-language.

Phase 1 needs both English and Nepali speech, fully offline and free. No single
free engine covers both well:

- **English (`en`)** → **MMS-TTS** (`facebook/mms-tts-eng`, a VITS model). Fast,
  single-shot, good quality.
- **Nepali (`ne`)** → **SpeechT5** finetuned on Nepali
  (`aryamanstha/speecht5_tts_nepali_...`) + the `microsoft/speecht5_hifigan`
  vocoder. Used because **MMS-TTS has no Nepali checkpoint** (`facebook/mms-tts-npi`
  does not exist — see `BLOCKERS.md`). SpeechT5 is built into `transformers`, so this
  needs no extra/forbidden dependencies.

The public contract — ``synthesize(text, language, out_path)`` — is identical
regardless of backend, so callers (pipeline/CLI/API) are engine-agnostic and a
different engine can be slotted in per language via config.

All models are lazy singletons; importing this module costs nothing and the unit
tests mock the whole thing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelLoadError, TTSError, UnsupportedLanguageError
from app.core.logging import get_logger
from app.schemas.pipeline import LANGUAGES, TTSResult

log = get_logger("services.tts")

# Which engine drives each language.
ENGINE_BY_LANG = {"en": "mms-tts", "ne": "speecht5"}

# Lazy singletons.
_MMS: Dict[str, object] = {}            # lang -> (tokenizer, model)
_SPEECHT5 = None                        # (tokenizer, model, vocoder, speaker_embedding)


# --------------------------------------------------------------------------- #
# MMS-TTS (VITS) — English
# --------------------------------------------------------------------------- #
def _load_mms(language: str, settings: Settings):
    if language in _MMS:
        return _MMS[language]
    try:
        from transformers import AutoTokenizer, VitsModel  # type: ignore

        name = settings.tts_model_en  # only 'en' uses MMS in Phase 1
        tok = AutoTokenizer.from_pretrained(name)
        model = VitsModel.from_pretrained(name).to(settings.resolved_device)
        _MMS[language] = (tok, model)
        log.info("TTS engine: MMS-TTS (%s, %s)", name, language)
        return _MMS[language]
    except ImportError as e:
        raise ModelLoadError("transformers/torch not installed — required for MMS-TTS.") from e
    except Exception as e:  # pragma: no cover - download/load failure
        raise ModelLoadError(f"Failed to load MMS-TTS model for '{language}': {e}") from e


def _synthesize_mms(text: str, language: str, settings: Settings) -> Tuple["object", int]:
    import torch  # type: ignore

    tok, model = _load_mms(language, settings)
    inputs = tok(text, return_tensors="pt").to(settings.resolved_device)
    with torch.no_grad():
        waveform = model(**inputs).waveform
    sr = int(model.config.sampling_rate)
    return waveform.squeeze().cpu().numpy(), sr


# --------------------------------------------------------------------------- #
# SpeechT5 + HiFi-GAN — Nepali
# --------------------------------------------------------------------------- #
def _load_speecht5(settings: Settings):
    global _SPEECHT5
    if _SPEECHT5 is not None:
        return _SPEECHT5
    try:
        import torch  # type: ignore
        from transformers import (  # type: ignore
            SpeechT5ForTextToSpeech,
            SpeechT5HifiGan,
            SpeechT5Tokenizer,
        )

        name = settings.tts_model_ne
        # The Nepali finetune ships only the tokenizer (no preprocessor_config),
        # which is all TTS needs — load the tokenizer directly.
        tok = SpeechT5Tokenizer.from_pretrained(name)
        model = SpeechT5ForTextToSpeech.from_pretrained(name).to(settings.resolved_device)
        vocoder = SpeechT5HifiGan.from_pretrained(settings.tts_vocoder).to(settings.resolved_device)

        # SpeechT5 requires a 512-dim speaker x-vector. Phase 1 has no speaker
        # preservation, so use a fixed, deterministic generic speaker.
        g = torch.Generator().manual_seed(settings.tts_speaker_seed)
        spk = torch.randn(1, 512, generator=g)
        spk = (spk / spk.norm()).to(settings.resolved_device)

        _SPEECHT5 = (tok, model, vocoder, spk)
        log.info("TTS engine: SpeechT5 (%s) + %s", name, settings.tts_vocoder)
        return _SPEECHT5
    except ImportError as e:
        raise ModelLoadError("transformers/torch not installed — required for SpeechT5 TTS.") from e
    except Exception as e:  # pragma: no cover - download/load failure
        raise ModelLoadError(f"Failed to load SpeechT5 Nepali TTS: {e}") from e


def _synthesize_speecht5(text: str, settings: Settings) -> Tuple["object", int]:
    import torch  # type: ignore

    tok, model, vocoder, spk = _load_speecht5(settings)
    input_ids = tok(text, return_tensors="pt")["input_ids"].to(settings.resolved_device)
    with torch.no_grad():
        speech = model.generate_speech(input_ids, spk, vocoder=vocoder)
    return speech.cpu().numpy(), 16000  # SpeechT5/HiFi-GAN output 16 kHz


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def synthesize(
    text: str,
    language: str,
    out_path: str | Path,
    settings: Settings | None = None,
) -> TTSResult:
    """Synthesize ``text`` in ``language`` ("en"/"ne") to a WAV at ``out_path``."""
    settings = settings or get_settings()
    if language not in LANGUAGES:
        raise UnsupportedLanguageError(
            f"Unsupported TTS language '{language}'. Supported: {list(LANGUAGES)}"
        )
    if not text.strip():
        raise TTSError("Cannot synthesize empty text.")

    engine = ENGINE_BY_LANG[language]
    try:
        import numpy as np  # type: ignore
        import scipy.io.wavfile  # type: ignore

        if engine == "mms-tts":
            waveform, sample_rate = _synthesize_mms(text, language, settings)
        else:  # speecht5 (Nepali)
            waveform, sample_rate = _synthesize_speecht5(text, settings)

        # Models emit float32 in ~[-1, 1]. Write PCM-16 so the WAV is universally
        # playable (stdlib `wave`, players) rather than float (WAVE_FORMAT 3).
        pcm = np.asarray(waveform, dtype=np.float32)
        peak = float(np.max(np.abs(pcm))) if pcm.size else 0.0
        if peak > 1.0:  # guard against clipping if a model overshoots
            pcm = pcm / peak
        pcm16 = (np.clip(pcm, -1.0, 1.0) * 32767.0).astype(np.int16)

        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        scipy.io.wavfile.write(str(out_path), rate=sample_rate, data=pcm16)
    except (UnsupportedLanguageError, TTSError, ModelLoadError):
        raise
    except Exception as e:
        raise TTSError(f"TTS synthesis failed ({engine}): {e}") from e

    if not Path(out_path).exists() or Path(out_path).stat().st_size == 0:
        raise TTSError(f"TTS produced no audio at {out_path}")

    return TTSResult(
        audio_path=str(out_path),
        language=language,
        sample_rate=sample_rate,
        engine=engine,
    )
