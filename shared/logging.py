"""Generic structured logging shared by both services.

Pipeline-specific helpers (e.g. StageTimer) live in Voice_ML; this module holds
only the generic console+JSON-file setup so neither service duplicates it.
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

_CONFIGURED = False


class JsonFormatter(logging.Formatter):
    """Compact JSON log lines — easy to grep and machine-parse."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for attr in ("stage", "duration_s"):
            if hasattr(record, attr):
                payload[attr] = getattr(record, attr)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(
    logs_dir: Optional[Path] = None,
    level: int = logging.INFO,
    log_filename: str = "service.log",
) -> None:
    """Configure root logging once (idempotent): console + optional rotating JSON file."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(level)

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(console)

    if logs_dir is not None:
        Path(logs_dir).mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            Path(logs_dir) / log_filename,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(JsonFormatter())
        root.addHandler(file_handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
