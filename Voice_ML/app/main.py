"""Voice_ML — FastAPI inference service.

Owns ALL machine-learning execution (ASR, translation, TTS, and — Phase 2 —
speaker-preserved voice conversion). The backend calls this service over HTTP; no
ML runs in Voice_backend.

Endpoints:
  GET  /ml/v1/health     — readiness + device/ffmpeg/model info
  POST /ml/v1/translate  — run the full pipeline on a video path, return artifacts
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app import __version__
from app.core.config import get_settings
from app.core.exceptions import InvalidVideoError, PipelineError, UnsupportedLanguageError
from app.core.logging import configure_logging, get_logger
from app.pipelines import (
    cloning_pipeline,
    localization_pipeline,
    speaker_preservation_pipeline,
    translation_pipeline,
)
from shared.contracts import MLTranslateRequest, MLTranslateResponse, StageTimings
from shared.languages import LANGUAGES

log = get_logger("ml.main")


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_dirs()
    configure_logging(settings.logs_dir)

    app = FastAPI(title="Voice_ML Inference Service", version=__version__)

    @app.get("/ml/v1/health")
    def health() -> dict:
        return {
            "status": "ok",
            "service": "voice_ml",
            "device": settings.resolved_device,
            "ffmpeg": settings.ffmpeg_available(),
            "languages": list(LANGUAGES),
        }

    @app.post("/ml/v1/translate", response_model=MLTranslateResponse)
    def translate(req: MLTranslateRequest) -> MLTranslateResponse:
        try:
            if req.localize:
                result = localization_pipeline.run_pipeline(
                    video_path=req.video_path,
                    target_language=req.target_language,
                    source_language=req.source_language,
                    job_id=req.job_id,
                    settings=settings,
                    speaker_sample=req.speaker_sample,
                )
            elif req.clone_voice:
                result = cloning_pipeline.run_pipeline(
                    video_path=req.video_path,
                    target_language=req.target_language,
                    source_language=req.source_language,
                    job_id=req.job_id,
                    settings=settings,
                    speaker_sample=req.speaker_sample,
                )
            elif req.preserve_voice:
                result = speaker_preservation_pipeline.run_pipeline(
                    video_path=req.video_path,
                    target_language=req.target_language,
                    source_language=req.source_language,
                    job_id=req.job_id,
                    settings=settings,
                )
            else:
                result = translation_pipeline.run_pipeline(
                    video_path=req.video_path,
                    target_language=req.target_language,
                    source_language=req.source_language,
                    job_id=req.job_id,
                    settings=settings,
                )
        except (UnsupportedLanguageError, InvalidVideoError) as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except PipelineError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

        return MLTranslateResponse(
            job_id=result.job_id,
            source_language=result.source_language,
            target_language=result.target_language,
            output_video=result.output_video,
            transcript_text=result.transcript_text,
            translated_text=result.translated_text,
            artifacts_dir=result.artifacts_dir,
            preserve_voice=result.preserve_voice,
            similarity=result.similarity,
            timings=StageTimings(**result.timings.model_dump()),
        )

    @app.exception_handler(PipelineError)
    async def _pipeline_error_handler(_request, exc: PipelineError):
        return JSONResponse(status_code=500, content={"status": "failed", "error": str(exc)})

    return app


app = create_app()
