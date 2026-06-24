"""Object storage abstraction (MinIO in prod, local filesystem in dev/tests).

Both backends implement the same interface so callers (upload API, worker) are
storage-agnostic. ``local`` stores under ``storage_dir``; ``minio`` uses an
S3-compatible bucket. Select via ``VC_STORAGE_BACKEND``.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from app.core.config import Settings, get_settings
from shared.logging import get_logger

log = get_logger("services.storage")


class Storage(ABC):
    @abstractmethod
    def put_file(self, key: str, src_path: str | Path, content_type: str | None = None) -> str: ...

    @abstractmethod
    def get_file(self, key: str, dest_path: str | Path) -> str: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorage(Storage):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents and p != self.root.resolve():
            raise ValueError(f"Unsafe storage key: {key}")  # path traversal guard
        return p

    def put_file(self, key, src_path, content_type=None) -> str:
        dest = self._p(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, dest)
        return key

    def get_file(self, key, dest_path) -> str:
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._p(key), dest_path)
        return str(dest_path)

    def delete(self, key) -> None:
        self._p(key).unlink(missing_ok=True)

    def exists(self, key) -> bool:
        return self._p(key).exists()


class MinioStorage(Storage):  # pragma: no cover - exercised only with a live MinIO
    def __init__(self, settings: Settings):
        from minio import Minio  # lazy import

        self.bucket = settings.minio_bucket
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_file(self, key, src_path, content_type=None) -> str:
        self.client.fput_object(self.bucket, key, str(src_path),
                                content_type=content_type or "application/octet-stream")
        return key

    def get_file(self, key, dest_path) -> str:
        Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
        self.client.fget_object(self.bucket, key, str(dest_path))
        return str(dest_path)

    def delete(self, key) -> None:
        self.client.remove_object(self.bucket, key)

    def exists(self, key) -> bool:
        try:
            self.client.stat_object(self.bucket, key)
            return True
        except Exception:
            return False


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    s = get_settings()
    if s.storage_backend == "minio":
        log.info("storage backend: MinIO (%s/%s)", s.minio_endpoint, s.minio_bucket)
        return MinioStorage(s)
    log.info("storage backend: local (%s)", s.storage_dir)
    return LocalStorage(s.storage_dir)
