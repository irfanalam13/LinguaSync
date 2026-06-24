"""Pydantic DTOs for the backend↔ML HTTP contract."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class StageTimings(BaseModel):
    """Wall-clock seconds per pipeline stage (shared across services)."""

    audio_extraction: float = 0.0
    transcription: float = 0.0
    translation: float = 0.0
    tts: float = 0.0
    voice_conversion: float = 0.0  # Phase 2/3: OpenVoice tone-color / cloning
    lip_sync: float = 0.0          # Phase 4: Wav2Lip
    video_render: float = 0.0
    total: float = 0.0


class MLTranslateRequest(BaseModel):
    """Backend → ML inference request."""

    video_path: str = Field(..., description="Absolute path to the input video (shared volume)")
    target_language: str
    source_language: Optional[str] = None
    preserve_voice: bool = False       # Phase 2: tone-color preservation
    clone_voice: bool = False          # Phase 3: identity cloning (multi-reference)
    localize: bool = False             # Phase 4: clone + Wav2Lip lip-sync
    speaker_sample: Optional[str] = None  # Phase 3: optional separate enrollment clip
    job_id: Optional[str] = None


class MLTranslateResponse(BaseModel):
    """ML → Backend inference result."""

    job_id: str
    source_language: str
    target_language: str
    output_video: str
    transcript_text: str
    translated_text: str
    artifacts_dir: str
    preserve_voice: bool = False
    similarity: Optional[float] = None  # speaker similarity (Phase 2), 0..1
    timings: StageTimings
