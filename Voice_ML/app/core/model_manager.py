"""Centralized model cache (lazy loading, CPU/GPU, no repeated loads).

A process-wide registry that loads each model once on first request and returns the
cached instance thereafter. Services pass a ``loader`` callable; the manager handles
caching and device selection. Keeps heavy models (s3fd, ECAPA, etc.) from being
re-instantiated per request.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from typing import Any, Callable, Dict

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

log = get_logger("core.model_manager")


class ModelManager:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()

    @property
    def device(self) -> str:
        return self.settings.resolved_device

    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        """Return cached model for ``key``, loading it once via ``loader`` if absent."""
        if key in self._cache:
            return self._cache[key]
        with self._lock:
            if key not in self._cache:  # double-checked
                log.info("loading model '%s' (device=%s)", key, self.device)
                self._cache[key] = loader()
        return self._cache[key]

    def has(self, key: str) -> bool:
        return key in self._cache

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


@lru_cache(maxsize=1)
def get_model_manager() -> ModelManager:
    return ModelManager()
