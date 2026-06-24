"""Voice cloning (Phase 3) — clone a speaker's identity onto translated speech.

Uses the speaker profile's **multi-reference** OpenVoice SE (richer than Phase 2's
single-reference timbre) to convert base-TTS audio into the target speaker's voice.

Primary engine: OpenVoice V2 (multi-reference). XTTS-v2 is the documented secondary
engine (isolated) if OpenVoice can't reach target quality — see PHASE3_ANALYSIS.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.services import speaker_profile_service, voice_preservation_service

log = get_logger("services.voice_clone")

ENGINE = "openvoice-v2-multiref"


def clone_to_profile(
    base_audio: str | Path,
    profile: Dict,
    out_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Clone ``base_audio`` to the speaker identity captured in ``profile``.

    Args:
        base_audio: base-TTS output (translated speech, generic voice).
        profile: speaker profile dict (from speaker_profile_service.build_profile).
        out_path: destination WAV for the cloned voice.
    """
    settings = settings or get_settings()
    target_se = speaker_profile_service.load_se(profile, settings)
    log.info("cloning voice -> speaker %s (engine=%s)", profile.get("speaker_id"), ENGINE)
    return voice_preservation_service.convert_with_se(base_audio, target_se, out_path, settings)
