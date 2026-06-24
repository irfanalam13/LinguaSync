"""Text translation with NLLB-200 (No Language Left Behind).

Uses HuggingFace ``transformers`` (``facebook/nllb-200-distilled-600M`` by
default). Supports English <-> Nepali. The model/tokenizer are lazy singletons,
so importing this module costs nothing and tests can mock the translator.

Long inputs are translated segment-by-segment (split on sentence boundaries) and
re-joined, because NLLB has a finite max sequence length.
"""

from __future__ import annotations

import re
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ModelLoadError,
    TranslationError,
    UnsupportedLanguageError,
)
from app.core.logging import get_logger
from app.schemas.pipeline import LANGUAGES, TranslationResult

log = get_logger("services.translation")

_MODEL = None
_TOKENIZER = None
_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+")  # includes Devanagari danda (।)


def _load(settings: Settings):
    global _MODEL, _TOKENIZER
    if _MODEL is not None:
        return
    try:
        import torch  # type: ignore  # noqa: F401
        from transformers import (  # type: ignore
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
        )

        _TOKENIZER = AutoTokenizer.from_pretrained(settings.translation_model)
        _MODEL = AutoModelForSeq2SeqLM.from_pretrained(settings.translation_model)
        _MODEL.to(settings.resolved_device)
        log.info("Translation backend: NLLB (%s)", settings.translation_model)
    except ImportError as e:
        raise ModelLoadError(
            "transformers/torch not installed — required for NLLB translation."
        ) from e
    except Exception as e:  # pragma: no cover - download/load failure
        raise ModelLoadError(f"Failed to load translation model: {e}") from e


def _chunk(text: str, max_words: int = 40) -> list[str]:
    """Split text into translator-sized chunks.

    First split on sentence boundaries (incl. the Devanagari danda ।). ASR output
    is often *unpunctuated* (one long run-on), which makes NLLB degenerate into
    repetition loops, so any over-long sentence is further split into word windows.
    """
    sentences = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if not sentences:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    for sentence in sentences:
        words = sentence.split()
        if len(words) <= max_words:
            chunks.append(sentence)
        else:
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))
    return chunks


def translate(
    text: str,
    source: str,
    target: str,
    settings: Settings | None = None,
) -> TranslationResult:
    """Translate ``text`` from ``source`` to ``target`` (ISO-639-1 "en"/"ne")."""
    settings = settings or get_settings()

    for code in (source, target):
        if code not in LANGUAGES:
            raise UnsupportedLanguageError(
                f"Unsupported language '{code}'. Supported: {list(LANGUAGES)}"
            )
    if source == target:
        raise UnsupportedLanguageError("Source and target languages must differ.")

    if not text.strip():
        return TranslationResult(source_language=source, target_language=target, translated_text="")

    _load(settings)

    src_code = LANGUAGES[source]["nllb"]
    tgt_code = LANGUAGES[target]["nllb"]

    try:
        _TOKENIZER.src_lang = src_code  # type: ignore[union-attr]
        bos = _TOKENIZER.convert_tokens_to_ids(tgt_code)  # type: ignore[union-attr]

        outputs: list[str] = []
        for chunk in _chunk(text):
            encoded = _TOKENIZER(  # type: ignore[union-attr]
                chunk,
                return_tensors="pt",
                truncation=True,
                max_length=settings.translation_max_length,
            ).to(settings.resolved_device)
            generated = _MODEL.generate(  # type: ignore[union-attr]
                **encoded,
                forced_bos_token_id=bos,
                max_length=settings.translation_max_length,
                num_beams=5,
                # Guard against the seq2seq repetition-loop failure mode on noisy
                # or unpunctuated ASR text (e.g. "my servant, my servant, ...").
                no_repeat_ngram_size=3,
                repetition_penalty=1.3,
            )
            decoded = _TOKENIZER.batch_decode(  # type: ignore[union-attr]
                generated, skip_special_tokens=True
            )
            outputs.append(decoded[0].strip())

        translated = " ".join(outputs).strip()
    except Exception as e:
        raise TranslationError(f"Translation failed: {e}") from e

    return TranslationResult(
        source_language=source,
        target_language=target,
        translated_text=translated,
    )
