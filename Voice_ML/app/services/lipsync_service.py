"""Lip synchronization via Wav2Lip.

Drives the vendored Wav2Lip ``inference.py`` (face video + audio → lip-synced video).
Run as a subprocess with the *same* venv Python and an environment whose PATH includes
the ffmpeg directory (Wav2Lip shells out to ``ffmpeg`` by name; on Windows + shell=True
it must be resolvable by cmd.exe).

Wav2Lip is CPU-heavy; the localization pipeline downscales the face video first.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import ModelLoadError, PipelineError
from app.core.logging import get_logger

log = get_logger("services.lipsync")

ENGINE = "wav2lip"


class LipSyncError(PipelineError):
    """Raised when Wav2Lip lip-sync fails."""


def _env_with_ffmpeg(settings: Settings) -> dict:
    """Copy the environment and prepend ffmpeg's dir to PATH (Windows-resolvable)."""
    env = dict(os.environ)
    ffmpeg_dir = str(Path(settings.ffmpeg_path).parent)
    if ffmpeg_dir and ffmpeg_dir != ".":
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def lipsync(
    face_video: str | Path,
    audio_path: str | Path,
    out_path: str | Path,
    settings: Settings | None = None,
    nosmooth: bool = True,
) -> str:
    """Lip-sync ``face_video`` to ``audio_path`` with Wav2Lip → ``out_path``."""
    settings = settings or get_settings()
    wav2lip_dir = Path(settings.wav2lip_dir)
    ckpt = Path(settings.wav2lip_checkpoint)
    if not (wav2lip_dir / "inference.py").exists() or not ckpt.exists():
        raise ModelLoadError(
            f"Wav2Lip not available (need {wav2lip_dir}/inference.py and {ckpt}). "
            f"See PHASE4_ANALYSIS.md."
        )

    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "inference.py",
        "--checkpoint_path", str(ckpt),
        "--face", str(Path(face_video).resolve()),
        "--audio", str(Path(audio_path).resolve()),
        "--outfile", str(out_path),
        "--face_det_batch_size", "4",
        "--wav2lip_batch_size", "16",
    ]
    if nosmooth:
        cmd.append("--nosmooth")

    log.info("running Wav2Lip: face=%s audio=%s", Path(face_video).name, Path(audio_path).name)
    proc = subprocess.run(
        cmd,
        cwd=str(wav2lip_dir),
        env=_env_with_ffmpeg(settings),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",  # Wav2Lip/tqdm emit bytes cp1252 can't decode on Windows
    )
    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
        tail = (proc.stdout or "").strip()[-800:]
        raise LipSyncError(f"Wav2Lip failed (exit {proc.returncode}): {tail}")
    return str(out_path)
