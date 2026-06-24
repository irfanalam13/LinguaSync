"""Video/audio processing via ffmpeg.

Replaces the original ``shell=True`` f-string implementation. All ffmpeg calls
use **argv lists** (no shell), so paths with spaces are safe and there is no
command-injection surface. Every call checks the return code and raises a
domain exception with the captured stderr on failure.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AudioExtractionError,
    FFmpegNotFoundError,
    InvalidVideoError,
    VideoRenderError,
)
from app.core.logging import get_logger
from app.schemas.pipeline import VideoMetadata

log = get_logger("services.video")


def _run(cmd: List[str], *, error_cls, action: str) -> subprocess.CompletedProcess:
    """Run an ffmpeg/ffprobe argv list, raising ``error_cls`` on failure."""
    log.debug("exec: %s", " ".join(cmd))
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as e:  # binary missing
        raise FFmpegNotFoundError(
            f"'{cmd[0]}' not found. Install ffmpeg and/or set VC_FFMPEG_PATH."
        ) from e
    if proc.returncode != 0:
        raise error_cls(f"{action} failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    return proc


def validate_video(video_path: str | Path, settings: Settings | None = None) -> None:
    """Raise if the file is missing/empty or ffmpeg is unavailable."""
    settings = settings or get_settings()
    p = Path(video_path)
    if not p.exists():
        raise InvalidVideoError(f"Input video does not exist: {p}")
    if p.stat().st_size == 0:
        raise InvalidVideoError(f"Input video is empty: {p}")
    if not settings.ffmpeg_available():
        raise FFmpegNotFoundError(
            f"ffmpeg ('{settings.ffmpeg_path}') is not on PATH. Install it to process video."
        )


def get_video_metadata(video_path: str | Path, settings: Settings | None = None) -> VideoMetadata:
    """Probe a video with ffprobe and return structured metadata."""
    settings = settings or get_settings()
    p = Path(video_path)
    cmd = [
        settings.ffprobe_path,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(p),
    ]
    proc = _run(cmd, error_cls=InvalidVideoError, action="ffprobe")
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as e:
        raise InvalidVideoError(f"Could not parse ffprobe output for {p}") from e

    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    duration = float(data.get("format", {}).get("duration", 0.0) or 0.0)

    return VideoMetadata(
        path=str(p),
        duration=duration,
        width=int(video_stream.get("width", 0)) if video_stream else 0,
        height=int(video_stream.get("height", 0)) if video_stream else 0,
        has_audio=has_audio,
        codec=video_stream.get("codec_name") if video_stream else None,
    )


def extract_audio(
    video_path: str | Path,
    audio_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Extract a mono WAV at the configured sample rate (ideal for ASR)."""
    settings = settings or get_settings()
    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-i", str(video_path),
        "-vn",                       # drop video
        "-ac", "1",                  # mono
        "-ar", str(settings.sample_rate),
        "-acodec", "pcm_s16le",
        str(audio_path),
    ]
    _run(cmd, error_cls=AudioExtractionError, action="audio extraction")
    if not Path(audio_path).exists() or Path(audio_path).stat().st_size == 0:
        raise AudioExtractionError(f"No audio produced from {video_path} (silent or no track?)")
    return str(audio_path)


def replace_audio(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Replace the video's audio track with ``audio_path`` (re-muxing).

    Video is stream-copied (fast, lossless); the output is trimmed to the shorter
    of the two streams so a longer/shorter dub does not leave dangling video.
    """
    settings = settings or get_settings()
    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_path),
    ]
    _run(cmd, error_cls=VideoRenderError, action="audio replacement")
    if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
        raise VideoRenderError(f"Output video not produced: {output_path}")
    return str(output_path)


# Backwards-compatible alias for the spec's name "merge_video_audio".
def merge_video_audio(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    settings: Settings | None = None,
) -> str:
    """Alias of :func:`replace_audio` (spec naming)."""
    return replace_audio(video_path, audio_path, output_path, settings)
