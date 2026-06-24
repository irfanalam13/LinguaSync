"""End-to-end translation pipeline orchestration.

    video.mp4
      -> extract audio          (video_service.extract_audio)
      -> speech-to-text         (transcription_service.transcribe)
      -> translate text         (translation_service.translate)
      -> text-to-speech         (tts_service.synthesize)
      -> merge audio with video (video_service.replace_audio)
      -> output.mp4

Every run writes the spec-mandated artifacts to ``artifacts/<job_id>/``::

    audio.wav  transcript.txt  translated.txt  translated.wav  output.mp4

and records per-stage timings. Source language can be forced or auto-detected;
target is required. Supports en->ne and ne->en.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import PipelineError, UnsupportedLanguageError
from app.core.logging import StageTimer, configure_logging, get_logger
from app.schemas.pipeline import LANGUAGES, PipelineResult, StageTimings
from app.services import transcription_service, translation_service, tts_service, video_service
from app.utils.files import job_artifacts_dir, new_job_id, write_text

log = get_logger("services.pipeline")

# Service callables are module attributes so tests can monkeypatch them cleanly.


def run_pipeline(
    video_path: str | Path,
    target_language: str,
    source_language: Optional[str] = None,
    job_id: Optional[str] = None,
    settings: Settings | None = None,
    progress: Optional[Callable[[str], None]] = None,
    preserve_voice: bool = False,
) -> PipelineResult:
    """Run the full translation pipeline and return a :class:`PipelineResult`.

    Args:
        video_path: input video.
        target_language: "en" or "ne".
        source_language: optional forced source; ``None`` = auto-detect from audio.
        job_id: optional id; generated if omitted.
        progress: optional callback invoked with a human-readable status per stage.
        preserve_voice: when True, run speaker-preserved synthesis (Phase 2). The
            actual tone-color conversion + similarity scoring is delegated to the
            speaker-preservation pipeline; this base pipeline records the flag.
    """
    settings = settings or get_settings()
    settings.ensure_dirs()
    configure_logging(settings.logs_dir)

    if target_language not in LANGUAGES:
        raise UnsupportedLanguageError(
            f"Unsupported target language '{target_language}'. Supported: {list(LANGUAGES)}"
        )

    # Resolve to an absolute path up front so every ffmpeg stage references the
    # same file regardless of process cwd.
    video_path = Path(video_path).resolve()

    job_id = job_id or new_job_id()
    art = job_artifacts_dir(settings.artifacts_dir, job_id)
    audio_wav = art / "audio.wav"
    transcript_txt = art / "transcript.txt"
    translated_txt = art / "translated.txt"
    translated_wav = art / "translated.wav"
    output_mp4 = art / "output.mp4"

    def _emit(msg: str) -> None:
        log.info("[%s] %s", job_id, msg)
        if progress:
            progress(msg)

    timings = StageTimings()
    log.info("pipeline start job=%s target=%s src=%s", job_id, target_language, source_language)

    try:
        # 1) Validate + extract audio --------------------------------------
        _emit("validating video")
        video_service.validate_video(video_path, settings)
        _emit("extracting audio")
        with StageTimer("audio_extraction") as t:
            video_service.extract_audio(video_path, audio_wav, settings)
        timings.audio_extraction = t.elapsed

        # 2) Transcribe -----------------------------------------------------
        _emit("transcribing")
        with StageTimer("transcription") as t:
            transcription = transcription_service.transcribe(audio_wav, source_language, settings)
        timings.transcription = t.elapsed
        write_text(transcript_txt, transcription.text)
        detected_source = transcription.language

        if detected_source == target_language:
            raise UnsupportedLanguageError(
                f"Source and target are both '{target_language}'. Nothing to translate."
            )

        # 3) Translate ------------------------------------------------------
        _emit(f"translating {detected_source} -> {target_language}")
        with StageTimer("translation") as t:
            translation = translation_service.translate(
                transcription.text, detected_source, target_language, settings
            )
        timings.translation = t.elapsed
        write_text(translated_txt, translation.translated_text)

        # 4) Text-to-speech -------------------------------------------------
        _emit("synthesizing speech")
        with StageTimer("tts") as t:
            tts_service.synthesize(
                translation.translated_text, target_language, translated_wav, settings
            )
        timings.tts = t.elapsed

        # 5) Merge audio back into video ------------------------------------
        _emit("rendering final video")
        with StageTimer("video_render") as t:
            video_service.replace_audio(video_path, translated_wav, output_mp4, settings)
        timings.video_render = t.elapsed

        timings.total = round(
            timings.audio_extraction
            + timings.transcription
            + timings.translation
            + timings.tts
            + timings.voice_conversion
            + timings.video_render,
            3,
        )
        _emit("done")
        log.info("pipeline done job=%s total=%.3fs", job_id, timings.total)

        return PipelineResult(
            job_id=job_id,
            source_language=detected_source,
            target_language=target_language,
            output_video=str(output_mp4),
            transcript_text=transcription.text,
            translated_text=translation.translated_text,
            artifacts_dir=str(art),
            preserve_voice=preserve_voice,
            similarity=None,  # set by the speaker-preservation pipeline (Phase 2)
            timings=timings,
        )
    except PipelineError:
        log.exception("pipeline failed job=%s", job_id)
        raise
    except Exception as e:  # wrap anything unexpected
        log.exception("pipeline crashed job=%s", job_id)
        raise PipelineError(f"Unexpected pipeline failure: {e}") from e
