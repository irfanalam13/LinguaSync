"""Validate the artifacts produced by a pipeline run (Task 5).

Checks, for a given artifacts/<job_id>/ directory:
  - output.mp4 exists and is non-empty
  - translated.wav is a readable/playable WAV (and its duration)
  - transcript.txt and translated.txt exist and are non-empty
  - the output video duration is within tolerance of the source video duration

Prints a JSON summary and exits non-zero if any hard check fails.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import wave
from pathlib import Path

from app.core.config import get_settings


def _probe_duration(ffprobe: str, path: Path) -> float:
    cmd = [
        ffprobe, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", required=True, help="path to artifacts/<job_id>/")
    ap.add_argument("--source-video", required=True, help="original input video")
    ap.add_argument("--tolerance", type=float, default=1.5, help="allowed duration delta (s)")
    args = ap.parse_args()

    settings = get_settings()
    art = Path(args.artifacts)
    ffprobe = settings.ffprobe_path

    checks: dict[str, object] = {}
    hard_fail = False

    # File existence + non-empty.
    for name in ("audio.wav", "transcript.txt", "translated.txt", "translated.wav", "output.mp4"):
        p = art / name
        ok = p.exists() and p.stat().st_size > 0
        checks[f"{name}_exists_nonempty"] = ok
        hard_fail = hard_fail or not ok

    # translated.wav playable + duration.
    twav = art / "translated.wav"
    try:
        with wave.open(str(twav), "rb") as w:
            frames, rate = w.getnframes(), w.getframerate()
            wav_dur = frames / float(rate) if rate else 0.0
        checks["translated_wav_playable"] = True
        checks["translated_wav_duration_s"] = round(wav_dur, 2)
    except Exception as e:
        checks["translated_wav_playable"] = False
        checks["translated_wav_error"] = str(e)
        hard_fail = True

    # transcript / translation content lengths.
    for name in ("transcript.txt", "translated.txt"):
        try:
            checks[f"{name}_chars"] = len((art / name).read_text(encoding="utf-8"))
        except Exception:
            checks[f"{name}_chars"] = 0

    # Duration match: output vs source video.
    src_dur = _probe_duration(ffprobe, Path(args.source_video))
    out_dur = _probe_duration(ffprobe, art / "output.mp4")
    delta = abs(src_dur - out_dur)
    checks["source_video_duration_s"] = round(src_dur, 2)
    checks["output_video_duration_s"] = round(out_dur, 2)
    checks["duration_delta_s"] = round(delta, 2)
    checks["duration_within_tolerance"] = delta <= args.tolerance
    # Duration mismatch is a soft warning (dub length differs), not a hard fail.

    summary = {"artifacts": str(art), "hard_fail": hard_fail, "checks": checks}
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
