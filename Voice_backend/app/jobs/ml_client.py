"""HTTP client to the Voice_ML inference service.

This is the ONLY way the backend reaches ML; the backend never imports torch,
whisper, NLLB, TTS, or OpenVoice. All inference happens out-of-process in Voice_ML.
"""

from __future__ import annotations

from functools import lru_cache

import httpx

from app.core.config import Settings, get_settings
from shared.contracts import MLTranslateRequest, MLTranslateResponse


class MLServiceError(RuntimeError):
    """Raised when the ML service is unreachable or returns an error."""


class MLClient:
    def __init__(self, base_url: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s

    def health(self) -> dict:
        try:
            r = httpx.get(f"{self.base_url}/ml/v1/health", timeout=10.0)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            raise MLServiceError(f"ML service health check failed: {e}") from e

    def translate(self, req: MLTranslateRequest) -> MLTranslateResponse:
        try:
            r = httpx.post(
                f"{self.base_url}/ml/v1/translate",
                json=req.model_dump(),
                timeout=self.timeout_s,
            )
        except httpx.HTTPError as e:
            raise MLServiceError(f"ML service request failed: {e}") from e

        if r.status_code >= 400:
            detail = _safe_detail(r)
            raise MLServiceError(f"ML service error {r.status_code}: {detail}")
        return MLTranslateResponse(**r.json())


def _safe_detail(resp: httpx.Response) -> str:
    try:
        return resp.json().get("detail") or resp.json().get("error") or resp.text
    except Exception:
        return resp.text


@lru_cache(maxsize=1)
def get_ml_client(settings: Settings | None = None) -> MLClient:
    settings = settings or get_settings()
    return MLClient(settings.ml_service_url, settings.ml_timeout_s)
