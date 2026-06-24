"""Tests for face_detection_service — s3fd + cv2 are faked."""

from __future__ import annotations

import sys
import types

import pytest

from app.core.exceptions import InvalidVideoError
from app.core import model_manager
from app.services import face_detection_service as fds


@pytest.fixture(autouse=True)
def reset_models():
    model_manager.get_model_manager().clear()
    yield
    model_manager.get_model_manager().clear()


def _fake_cv2(monkeypatch, n_frames=5):
    fake = types.ModuleType("cv2")
    fake.CAP_PROP_FRAME_COUNT = 7
    fake.CAP_PROP_POS_FRAMES = 1

    class _Cap:
        def __init__(self, path):
            self._n = 0

        def get(self, prop):
            return 100.0

        def set(self, prop, val):
            pass

        def read(self):
            self._n += 1
            return (self._n <= n_frames, object())

        def release(self):
            pass

    fake.VideoCapture = lambda path: _Cap(path)
    monkeypatch.setitem(sys.modules, "cv2", fake)


def test_detect_missing_video(settings, tmp_path):
    with pytest.raises(InvalidVideoError):
        fds.detect_faces_in_video(tmp_path / "nope.mp4", settings)


def test_detect_face_present(settings, tmp_path, monkeypatch):
    _fake_cv2(monkeypatch)
    vid = tmp_path / "f.mp4"
    vid.write_bytes(b"\x00" * 64)

    class _Detector:
        def get_detections_for_batch(self, frames):
            return [(10, 10, 50, 50)] * len(frames)  # a box per frame

    monkeypatch.setattr(fds, "_load_detector", lambda s: _Detector())
    out = fds.detect_faces_in_video(vid, settings)
    assert out["speaking_face_present"] is True
    assert out["frames_with_face"] == out["frames_sampled"]


def test_detect_no_face(settings, tmp_path, monkeypatch):
    _fake_cv2(monkeypatch)
    vid = tmp_path / "f.mp4"
    vid.write_bytes(b"\x00" * 64)

    class _Detector:
        def get_detections_for_batch(self, frames):
            return [None] * len(frames)

    monkeypatch.setattr(fds, "_load_detector", lambda s: _Detector())
    out = fds.detect_faces_in_video(vid, settings)
    assert out["speaking_face_present"] is False
