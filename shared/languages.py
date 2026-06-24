"""Supported languages and their downstream model codes (Phase 1 + 2: en, ne)."""

from __future__ import annotations

# - Whisper/faster-whisper use ISO-639-1 ("en", "ne")
# - NLLB-200 uses FLORES codes ("eng_Latn", "npi_Deva")
LANGUAGES = {
    "en": {"name": "English", "nllb": "eng_Latn"},
    "ne": {"name": "Nepali", "nllb": "npi_Deva"},
}
