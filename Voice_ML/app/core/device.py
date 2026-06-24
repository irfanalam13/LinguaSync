"""Compute-device detection (CPU / CUDA GPU) with safe fallback.

Importing torch is optional: if it is not installed (e.g. during unit tests on a
machine without the ML stack), everything degrades to CPU rather than crashing.
"""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def detect_device() -> str:
    """Return ``"cuda"`` when a usable GPU is present, else ``"cpu"``.

    Never raises — a missing/old torch simply yields ``"cpu"``.
    """
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            return "cuda"
    except Exception:  # pragma: no cover - torch absent or broken
        pass
    return "cpu"


def resolve_device(preference: str = "auto") -> str:
    """Resolve a user device preference (``auto``/``cpu``/``cuda``) to a concrete device.

    ``cuda`` is honoured only if actually available; otherwise we fall back to CPU.
    """
    preference = (preference or "auto").lower()
    if preference == "cpu":
        return "cpu"
    if preference == "cuda":
        return detect_device()  # downgrades to cpu if no GPU
    return detect_device()


def compute_type_for(device: str) -> str:
    """Sensible faster-whisper compute type for a device."""
    return "float16" if device == "cuda" else "int8"
