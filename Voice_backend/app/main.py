"""Voice_backend — FastAPI API gateway (no ML inference in-process)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.routes import router as translate_router
from app.api.users import router as users_router
from app.api.videos import router as videos_router
from app.api.ws import router as ws_router
from app.core.config import get_settings
from shared.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    settings.ensure_dirs()
    configure_logging(settings.logs_dir, log_filename="backend.log")

    app = FastAPI(
        title="Voice Translation Platform — API Gateway",
        version=__version__,
        description="Phase 5 — production platform API. All ML inference runs in Voice_ML.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(videos_router)
    app.include_router(jobs_router)
    app.include_router(ws_router)
    app.include_router(translate_router)  # legacy direct-HTTP route (Phase 2)

    @app.get("/")
    def root() -> dict:
        return {"name": "voice-backend", "version": __version__, "docs": "/docs"}

    return app


app = create_app()
