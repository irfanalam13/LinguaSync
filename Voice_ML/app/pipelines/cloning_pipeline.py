"""Voice-cloning translation pipeline (Phase 3).

    (base) extract → ASR → translate → base TTS → mux
    (+)    speaker profile (30-s sample, multi-reference) → clone identity onto
           translated speech → dual-metric quality score → re-mux into output.mp4

Reuses `translation_pipeline` for the content path; the speaker sample defaults to the
source video's own audio, or a separate enrollment clip can be supplied.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import PipelineError
from app.core.logging import StageTimer, get_logger
from app.pipelines import translation_pipeline
from app.schemas.pipeline import PipelineResult
from app.services import (
    quality_evaluation_service,
    speaker_profile_service,
    video_service,
    voice_clone_service,
)

log = get_logger("pipelines.cloning")


def run_pipeline(
    video_path: str | Path,
    target_language: str,
    source_language: Optional[str] = None,
    job_id: Optional[str] = None,
    settings: Settings | None = None,
    progress: Optional[Callable[[str], None]] = None,
    speaker_sample: Optional[str | Path] = None,
    speaker_id: Optional[str] = None,
) -> PipelineResult:
    """Translate ``video_path`` and synthesize it in the source speaker's cloned voice."""
    settings = settings or get_settings()
    video_path = Path(video_path).resolve()

    def _emit(msg: str) -> None:
        if progress:
            progress(msg)

    # 1) Base translation (content path).
    base = translation_pipeline.run_pipeline(
        video_path, target_language, source_language, job_id, settings, progress,
        preserve_voice=False,
    )

    art = Path(base.artifacts_dir)
    sample = Path(speaker_sample).resolve() if speaker_sample else (art / "audio.wav")
    base_tts = art / "translated.wav"
    cloned = art / "cloned.wav"
    output = art / "output.mp4"

    try:
        with StageTimer("voice_conversion") as t:
            # 2) Build + persist the speaker profile (multi-reference).
            _emit("extracting speaker profile")
            profile = speaker_profile_service.build_profile(sample, speaker_id, settings)
            # 3) Clone the speaker's identity onto the translated speech.
            _emit("cloning voice")
            voice_clone_service.clone_to_profile(base_tts, profile, cloned, settings)

        # 4) Quality scoring (Resemblyzer + SpeechBrain).
        _emit("scoring clone quality")
        baseline = quality_evaluation_service.evaluate(sample, base_tts, settings)
        cloned_q = quality_evaluation_service.evaluate(sample, cloned, settings)
        (art / "cloning_quality.json").write_text(
            json.dumps(
                {
                    "speaker_id": profile["speaker_id"],
                    "num_reference_segments": profile["num_reference_segments"],
                    "baseline": baseline,
                    "cloned": cloned_q,
                    "improvement": round(cloned_q["similarity"] - baseline["similarity"], 4),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # 5) Re-mux cloned audio into the final video.
        _emit("rendering final video (cloned voice)")
        video_service.replace_audio(video_path, cloned, output, settings)
    except PipelineError:
        log.exception("cloning pipeline failed job=%s", base.job_id)
        raise

    timings = base.timings.model_copy()
    timings.voice_conversion = t.elapsed
    timings.total = round(timings.total + t.elapsed, 3)

    log.info(
        "cloning done job=%s speaker=%s baseline=%.4f cloned=%.4f (+%.4f)",
        base.job_id, profile["speaker_id"], baseline["similarity"], cloned_q["similarity"],
        cloned_q["similarity"] - baseline["similarity"],
    )

    return PipelineResult(
        job_id=base.job_id,
        source_language=base.source_language,
        target_language=base.target_language,
        output_video=str(output),
        transcript_text=base.transcript_text,
        translated_text=base.translated_text,
        artifacts_dir=str(art),
        preserve_voice=True,
        similarity=cloned_q["similarity"],
        timings=timings,
    )
