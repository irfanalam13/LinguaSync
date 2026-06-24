"""Cross-service contract shared by Voice_backend (API) and Voice_ML (inference).

Single source of truth for language codes and the HTTP request/response DTOs that
cross the backend↔ML boundary, so neither side duplicates the contract.
"""

from shared.languages import LANGUAGES
from shared.contracts import (
    MLTranslateRequest,
    MLTranslateResponse,
    StageTimings,
)

__all__ = [
    "LANGUAGES",
    "MLTranslateRequest",
    "MLTranslateResponse",
    "StageTimings",
]
