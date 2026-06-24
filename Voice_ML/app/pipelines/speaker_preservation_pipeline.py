"""Speaker-preserved translation pipeline (Phase 2).

Wraps the base translation pipeline, then transfers the original speaker's timbre
onto the translated speech with OpenVoice and re-muxes the result:

    (base) extract → ASR → translate → base TTS → mux
    (+)    OpenVoice tone-color conversion (base voice → original speaker)
           → speaker-similarity scoring → re-mux preserved audio into output.mp4

Reuses `translation_pipeline.run_pipeline` for everything up to the base TTS, so no
ASR/translation/TTS logic is duplicated.
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
from app.services import similarity_service, video_service, voice_preservation_service

log = get_logger("pipelines.speaker_preservation")


def run_pipeline(
    video_path: str | Path,
    target_language: str,
    source_language: Optional[str] = None,
    job_id: Optional[str] = None,
    settings: Settings | None = None,
    progress: Optional[Callable[[str], None]] = None,
) -> PipelineResult:
    """Run translation with speaker preservation; returns a result incl. similarity."""
    settings = settings or get_settings()
    video_path = Path(video_path).resolve()

    def _emit(msg: str) -> None:
        if progress:
            progress(msg)

    # 1) Base translation (extract → ASR → translate → base TTS → mux).
    base = translation_pipeline.run_pipeline(
        video_path, target_language, source_language, job_id, settings, progress,
        preserve_voice=False,
    )

    art = Path(base.artifacts_dir)
    source_audio = art / "audio.wav"       # original speaker (voice to preserve)
    base_tts = art / "translated.wav"      # base TTS (generic voice)
    preserved = art / "preserved.wav"
    output = art / "output.mp4"

    try:
        # 2) Tone-color conversion: base voice → original speaker.
        _emit("preserving speaker voice")
        with StageTimer("voice_conversion") as t:
            voice_preservation_service.preserve_voice(base_tts, source_audio, preserved, settings)

        # 3) Speaker similarity (baseline vs preserved).
        _emit("scoring speaker similarity")
        sim_before = similarity_service.compare_audio(source_audio, base_tts, settings)["similarity"]
        sim_after = similarity_service.compare_audio(source_audio, preserved, settings)["similarity"]
        (art / "similarity.json").write_text(
            json.dumps(
                {
                    "baseline_similarity": sim_before,
                    "preserved_similarity": sim_after,
                    "improvement": round(sim_after - sim_before, 4),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        # 4) Re-mux the preserved audio into the final video.
        _emit("rendering final video (preserved voice)")
        video_service.replace_audio(video_path, preserved, output, settings)
    except PipelineError:
        log.exception("speaker-preservation failed job=%s", base.job_id)
        raise

    timings = base.timings.model_copy()
    timings.voice_conversion = t.elapsed
    timings.total = round(timings.total + t.elapsed, 3)

    log.info(
        "preservation done job=%s baseline=%.4f preserved=%.4f (+%.4f)",
        base.job_id, sim_before, sim_after, sim_after - sim_before,
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
        similarity=sim_after,
        timings=timings,
    )
