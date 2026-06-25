"""Backend configuration (API gateway only — no model settings live here)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]  # .../Voice_backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VC_", env_file=".env", extra="ignore")

    uploads_dir: Path = BASE_DIR / "uploads"
    logs_dir: Path = BASE_DIR / "logs"

    # Voice_ML inference service (legacy direct HTTP; Phase 5 adds a Redis queue path).
    ml_service_url: str = "http://127.0.0.1:8001"
    ml_timeout_s: float = 3600.0  # CPU inference can be slow

    max_upload_mb: int = 500

    # ---- Database (Phase 5) ------------------------------------------------
    # SQLite by default for local/dev/tests; Postgres in prod via env, e.g.
    #   VC_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/voice_platform
    database_url: str = f"sqlite:///{(BASE_DIR / 'voice_platform.db').as_posix()}"
    db_echo: bool = False

    # ---- Redis / queue (Phase 5) ------------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    job_queue_name: str = "voice_jobs"
    # "eager" runs jobs inline (dev/tests, no Redis); "rq" enqueues to a Redis worker.
    queue_backend: str = "eager"

    # ---- Storage (Phase 5) -------------------------------------------------
    # "local" = filesystem (dev/tests); "minio" = S3-compatible object store.
    storage_backend: str = "local"
    storage_dir: Path = BASE_DIR / "storage_data"

    # ---- Auth / JWT (Phase 5) ---------------------------------------------
    jwt_secret: str = "dev-secret-change-me"  # override in prod via VC_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_ttl_min: int = 30
    refresh_token_ttl_days: int = 14

    # ---- Email / SMTP ------------------------------------------------------
    app_base_url: str = "http://localhost:3000"
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    email_from: str | None = None
    email_from_name: str = "Voice Converter"

    # ---- Object storage / MinIO (Phase 5) ---------------------------------
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "voice-platform"
    minio_secure: bool = False

    # ---- CORS (Phase 5 frontend) ------------------------------------------
    cors_origins: list[str] = ["http://localhost:3000"]

    def ensure_dirs(self) -> None:
        for d in (self.uploads_dir, self.logs_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
