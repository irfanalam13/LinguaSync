"""Video localization helpers (face-video prep + final assembly).

Prepares the input video's face track for tractable CPU Wav2Lip (downscale/fps/trim)
and provides small ffmpeg helpers. The heavy lip-sync itself lives in lipsync_service;
this module is the glue around it.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.exceptions import VideoRenderError
from app.core.logging import get_logger

log = get_logger("services.video_localization")


def prepare_face_video(
    input_video: str | Path,
    out_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Downscale/normalize the input video for CPU lip-sync (width, fps, optional trim).

    Wav2Lip runs per-frame face detection + a GAN; full-resolution video is impractical
    on CPU, so we cap width/fps (and optionally trim) per config.
    """
    settings = settings or get_settings()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    vf = f"scale={settings.lipsync_max_width}:-2,fps={settings.lipsync_fps}"
    cmd = [settings.ffmpeg_path, "-y"]
    if settings.lipsync_max_seconds and settings.lipsync_max_seconds > 0:
        cmd += ["-t", str(settings.lipsync_max_seconds)]
    cmd += ["-i", str(input_video), "-vf", vf, "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an", str(out_path)]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0 or not Path(out_path).exists():
        raise VideoRenderError(f"Face-video prep failed: {proc.stderr.strip()[:400]}")
    log.info("prepared face video: %s (w=%d fps=%d)", out_path, settings.lipsync_max_width, settings.lipsync_fps)
    return str(out_path)
