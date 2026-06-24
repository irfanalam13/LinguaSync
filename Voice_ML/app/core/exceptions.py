"""Domain exceptions for the translation pipeline.

Every failure mode the spec calls out maps to a specific exception so callers
(CLI, API) can turn it into a meaningful, actionable message instead of a bare
traceback. All inherit from :class:`PipelineError`.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for all pipeline failures."""


class FFmpegNotFoundError(PipelineError):
    """The ffmpeg binary could not be located or executed."""


class InvalidVideoError(PipelineError):
    """The input file is missing, unreadable, or not a valid video."""


class AudioExtractionError(PipelineError):
    """ffmpeg failed to extract an audio track from the video."""


class CorruptAudioError(PipelineError):
    """The extracted/loaded audio is empty or unreadable."""


class UnsupportedLanguageError(PipelineError):
    """A requested source/target language is not supported in Phase 1."""


class ModelLoadError(PipelineError):
    """A model (ASR / translation / TTS) failed to load."""


class TranscriptionError(PipelineError):
    """Speech-to-text failed."""


class TranslationError(PipelineError):
    """Text translation failed."""


class TTSError(PipelineError):
    """Text-to-speech synthesis failed."""


class VideoRenderError(PipelineError):
    """ffmpeg failed to merge the new audio back into the video."""
