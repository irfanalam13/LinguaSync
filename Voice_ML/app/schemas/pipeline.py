"""Pydantic models for data flowing through the pipeline.

These are the contracts between services. Using typed models (rather than loose
dicts) makes each stage's input/output explicit and keeps the API/CLI honest.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

# Single source of truth lives in the shared contract package.
from shared.contracts import StageTimings  # re-exported for existing imports
from shared.languages import LANGUAGES  # re-exported for existing imports

__all__ = [
    "LANGUAGES",
    "StageTimings",
    "SegmentSchema",
    "TranscriptionResult",
    "TranslationResult",
    "TTSResult",
    "VideoMetadata",
    "PipelineResult",
]


class SegmentSchema(BaseModel):
    """A single timestamped transcription segment."""

    start: float = Field(..., description="Segment start time in seconds")
    end: float = Field(..., description="Segment end time in seconds")
    text: str


class TranscriptionResult(BaseModel):
    """Output of the speech-to-text stage."""

    language: str = Field(..., description="Detected/forced ISO-639-1 language code")
    text: str
    segments: List[SegmentSchema] = Field(default_factory=list)


class TranslationResult(BaseModel):
    """Output of the translation stage."""

    source_language: str
    target_language: str
    translated_text: str


class TTSResult(BaseModel):
    """Output of the text-to-speech stage."""

    audio_path: str
    language: str
    sample_rate: int
    engine: str


class VideoMetadata(BaseModel):
    """Probed metadata for an input/output video."""

    path: str
    duration: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False
    codec: Optional[str] = None


class PipelineResult(BaseModel):
    """Final result of a full pipeline run."""

    job_id: str
    source_language: str
    target_language: str
    output_video: str
    transcript_text: str
    translated_text: str
    artifacts_dir: str
    preserve_voice: bool = False
    similarity: Optional[float] = None  # Phase 2 speaker similarity (0..1)
    timings: StageTimings
