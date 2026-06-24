"""Full video localization pipeline (Phase 4).

    input video → (Phase 3 cloning_pipeline: ASR → translate → clone voice)
                → prepare face video → face detection → Wav2Lip lip-sync to cloned audio
                → final_output.mp4

Reuses `cloning_pipeline` for everything up to the cloned audio; adds the visual
lip-sync stage. Produces the spec artifacts: original.mp4, translated.wav, cloned.wav,
lipsync.mp4, final_output.mp4.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import PipelineError
from app.core.logging import StageTimer, get_logger
from app.pipelines import cloning_pipeline
from app.schemas.pipeline import PipelineResult
from app.services import face_detection_service, lipsync_service, video_localization_service

log = get_logger("pipelines.localization")


class FaceMissingError(PipelineError):
    """Raised when the input video has no detectable face to lip-sync."""


def run_pipeline(
    video_path: str | Path,
    target_language: str,
    source_language: Optional[str] = None,
    job_id: Optional[str] = None,
    settings: Settings | None = None,
    progress: Optional[Callable[[str], None]] = None,
    speaker_sample: Optional[str | Path] = None,
) -> PipelineResult:
    """Translate + clone + lip-sync a video into a fully localized `final_output.mp4`."""
    settings = settings or get_settings()
    video_path = Path(video_path).resolve()

    def _emit(msg: str) -> None:
        if progress:
            progress(msg)

    # 1) Phase 3 cloning (ASR → translate → clone voice → output.mp4).
    base = cloning_pipeline.run_pipeline(
        video_path, target_language, source_language, job_id, settings, progress,
        speaker_sample=speaker_sample,
    )
    art = Path(base.artifacts_dir)
    cloned = art / "cloned.wav"
    face_small = art / "face_small.mp4"
    lipsync_out = art / "lipsync.mp4"
    final_out = art / "final_output.mp4"

    try:
        # 2) Preserve a copy of the original input as an artifact.
        shutil.copyfile(video_path, art / "original.mp4")

        # 3) Prepare (downscale) the face video for CPU Wav2Lip.
        _emit("preparing face video")
        video_localization_service.prepare_face_video(video_path, face_small, settings)

        # 4) Face detection / validation.
        _emit("detecting face")
        face_info = face_detection_service.detect_faces_in_video(face_small, settings)
        if not face_info["speaking_face_present"]:
            raise FaceMissingError(
                f"No face detected in {video_path.name}; lip-sync requires a talking-face video."
            )

        # 5) Lip-sync the cloned audio onto the face video.
        _emit("lip-syncing (Wav2Lip)")
        with StageTimer("lip_sync") as t:
            lipsync_service.lipsync(face_small, cloned, lipsync_out, settings)

        # 6) Final output = the lip-synced video (already carries the cloned audio).
        shutil.copyfile(lipsync_out, final_out)
    except PipelineError:
        log.exception("localization failed job=%s", base.job_id)
        raise

    timings = base.timings.model_copy()
    timings.lip_sync = t.elapsed
    timings.total = round(timings.total + t.elapsed, 3)

    log.info("localization done job=%s final=%s", base.job_id, final_out)

    return PipelineResult(
        job_id=base.job_id,
        source_language=base.source_language,
        target_language=base.target_language,
        output_video=str(final_out),
        transcript_text=base.transcript_text,
        translated_text=base.translated_text,
        artifacts_dir=str(art),
        preserve_voice=True,
        similarity=base.similarity,
        timings=timings,
    )
