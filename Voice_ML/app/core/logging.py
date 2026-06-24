"""Voice_ML logging: generic setup from `shared` + pipeline stage timing.

The console/JSON-file configuration is shared with the backend (``shared.logging``);
only the pipeline-specific :class:`StageTimer` lives here.
"""

from __future__ import annotations

import logging
import time
from contextlib import ContextDecorator
from typing import Optional

from shared.logging import JsonFormatter, configure_logging, get_logger  # noqa: F401

__all__ = ["JsonFormatter", "configure_logging", "get_logger", "StageTimer"]


class StageTimer(ContextDecorator):
    """Times a pipeline stage and records the elapsed seconds.

    Usage::

        with StageTimer("transcription") as t:
            ...
        print(t.elapsed)
    """

    def __init__(self, stage: str, logger: Optional[logging.Logger] = None):
        self.stage = stage
        self.logger = logger or get_logger("pipeline.timing")
        self.elapsed: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "StageTimer":
        self._start = time.perf_counter()
        self.logger.info("stage start: %s", self.stage, extra={"stage": self.stage})
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.elapsed = round(time.perf_counter() - self._start, 3)
        self.logger.info(
            "stage done: %s (%.3fs)",
            self.stage,
            self.elapsed,
            extra={"stage": self.stage, "duration_s": self.elapsed},
        )
        return False  # never suppress exceptions
