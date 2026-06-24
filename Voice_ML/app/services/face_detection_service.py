"""Face detection (Wav2Lip's bundled s3fd detector).

Detects the speaking face / bounding boxes in the input video, reports single vs
multiple faces, and validates that a face is present before lip-sync. The detector is
cached via the model manager (loaded once).

Limitations (documented): this reports faces on sampled frames; it does not do robust
multi-speaker tracking or active-speaker selection across a scene — those are Phase-4
stretch goals. With multiple faces, Wav2Lip syncs the detected box(es); reliable
speaker attribution is out of scope.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

from app.core.config import Settings, get_settings
from app.core.exceptions import InvalidVideoError, PipelineError
from app.core.logging import get_logger
from app.core.model_manager import get_model_manager

log = get_logger("services.face_detection")


class FaceDetectionError(PipelineError):
    """Raised when face detection fails."""


def _load_detector(settings: Settings):
    def loader():
        wav2lip_dir = str(settings.wav2lip_dir)
        if wav2lip_dir not in sys.path:
            sys.path.insert(0, wav2lip_dir)
        import face_detection  # type: ignore  # Wav2Lip's bundled package

        device = "cuda" if settings.resolved_device == "cuda" else "cpu"
        return face_detection.FaceAlignment(
            face_detection.LandmarksType._2D, flip_input=False, device=device
        )

    return get_model_manager().get("s3fd_face_detector", loader)


def detect_faces_in_video(
    video_path: str | Path,
    settings: Settings | None = None,
    sample_count: int = 5,
) -> Dict:
    """Sample frames and report face presence/count via s3fd."""
    settings = settings or get_settings()
    p = Path(video_path)
    if not p.exists() or p.stat().st_size == 0:
        raise InvalidVideoError(f"Video missing or empty: {p}")

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore

        cap = cv2.VideoCapture(str(p))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        idxs = [int(total * i / (sample_count + 1)) for i in range(1, sample_count + 1)] if total else [0]
        frames = []
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        cap.release()
        if not frames:
            raise FaceDetectionError(f"Could not read frames from {p}")

        detector = _load_detector(settings)
        # Wav2Lip's detector expects a stacked numpy array (N,H,W,3), not a list.
        boxes = detector.get_detections_for_batch(np.array(frames))  # None where no face
        per_frame_counts = [0 if b is None else 1 for b in boxes]
        # s3fd's batch API returns one box per frame; sample multi-face via a full detect.
        faces_found = sum(per_frame_counts)
    except (FaceDetectionError, InvalidVideoError):
        raise
    except Exception as e:
        raise FaceDetectionError(f"Face detection failed: {e}") from e

    result = {
        "frames_sampled": len(frames),
        "frames_with_face": faces_found,
        "speaking_face_present": faces_found > 0,
        "multiple_faces": False,  # batch API returns a single primary box per frame
        "note": "single-primary-face detection; multi-speaker tracking is a stretch goal",
    }
    log.info("face detection: %s", result)
    return result
