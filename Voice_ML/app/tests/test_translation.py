"""Tests for translation_service — NLLB model/tokenizer are faked."""

from __future__ import annotations

import pytest

from app.core.exceptions import TranslationError, UnsupportedLanguageError
from app.services import translation_service as tr


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    monkeypatch.setattr(tr, "_MODEL", None)
    monkeypatch.setattr(tr, "_TOKENIZER", None)


def _install_fake(monkeypatch, mapping=None):
    """Install a fake tokenizer/model that 'translates' by lookup or marker."""
    mapping = mapping or {}

    class _Encoded(dict):
        def to(self, device):
            return self

    class _Tok:
        src_lang = None

        def __call__(self, text, **kw):
            self._last = text
            return _Encoded(text=text)

        def convert_tokens_to_ids(self, code):
            return 7

        def batch_decode(self, generated, **kw):
            src = generated["text"]
            return [mapping.get(src, f"<{src}>")]

    class _Model:
        def generate(self, **kw):
            return {"text": kw["text"]}

    monkeypatch.setattr(tr, "_TOKENIZER", _Tok())
    monkeypatch.setattr(tr, "_MODEL", _Model())
    monkeypatch.setattr(tr, "_load", lambda settings: None)


def test_translate_en_to_ne(settings, monkeypatch):
    _install_fake(monkeypatch, {"Hello world.": "नमस्ते संसार।"})
    result = tr.translate("Hello world.", "en", "ne", settings)
    assert result.source_language == "en"
    assert result.target_language == "ne"
    assert result.translated_text == "नमस्ते संसार।"


def test_translate_ne_to_en(settings, monkeypatch):
    _install_fake(monkeypatch, {"नमस्ते।": "Hello."})
    result = tr.translate("नमस्ते।", "ne", "en", settings)
    assert result.translated_text == "Hello."


def test_translate_multi_sentence_joins(settings, monkeypatch):
    _install_fake(monkeypatch, {"One.": "एक।", "Two.": "दुई।"})
    result = tr.translate("One. Two.", "en", "ne", settings)
    assert result.translated_text == "एक। दुई।"


def test_translate_empty_text_short_circuits(settings, monkeypatch):
    # _load must never be called for empty input.
    monkeypatch.setattr(tr, "_load", lambda s: (_ for _ in ()).throw(AssertionError("loaded")))
    result = tr.translate("   ", "en", "ne", settings)
    assert result.translated_text == ""


def test_translate_unsupported_language(settings):
    with pytest.raises(UnsupportedLanguageError):
        tr.translate("hi", "en", "fr", settings)


def test_translate_same_language_rejected(settings):
    with pytest.raises(UnsupportedLanguageError):
        tr.translate("hi", "en", "en", settings)


def test_translate_wraps_backend_errors(settings, monkeypatch):
    class _Tok:
        src_lang = None

        def __call__(self, *a, **k):
            raise RuntimeError("tokenize fail")

        def convert_tokens_to_ids(self, c):
            return 1

    monkeypatch.setattr(tr, "_TOKENIZER", _Tok())
    monkeypatch.setattr(tr, "_MODEL", object())
    monkeypatch.setattr(tr, "_load", lambda settings: None)
    with pytest.raises(TranslationError):
        tr.translate("hello", "en", "ne", settings)
