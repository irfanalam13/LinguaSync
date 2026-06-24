"""Create a real spoken-audio sample video, fully offline.

We synthesize speech with the project's own MMS-TTS engine and mux it onto a
generated test-pattern video via ffmpeg. This gives a genuine video with a real
speech track to feed the pipeline end-to-end, with no external downloads.

Usage:
    python -m scripts.make_sample_video --lang en --out artifacts/_samples/sample_en.mp4
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from app.core.config import get_settings
from app.services import tts_service, video_service

SENTENCES = {
    "en": "The weather today is bright and sunny. Many people are walking in the park near the river.",
    "ne": "आजको मौसम धेरै राम्रो छ। मानिसहरू नदी नजिकको पार्कमा हिँडिरहेका छन्।",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["en", "ne"])
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    settings = get_settings()
    settings.ensure_dirs()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # 1) Synthesize the spoken track with MMS-TTS.
    voice_wav = out.with_suffix(".voice.wav")
    print(f"[make] synthesizing {args.lang} speech -> {voice_wav}")
    res = tts_service.synthesize(SENTENCES[args.lang], args.lang, voice_wav, settings)
    print(f"[make] tts engine={res.engine} sr={res.sample_rate}")

    # 2) Probe its duration via ffprobe.
    dur_cmd = [
        settings.ffprobe_path, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(voice_wav),
    ]
    duration = float(subprocess.run(dur_cmd, capture_output=True, text=True).stdout.strip())
    print(f"[make] audio duration = {duration:.2f}s")

    # 3) Generate a test-pattern video of that length and mux the speech in.
    cmd = [
        settings.ffmpeg_path, "-y",
        "-f", "lavfi", "-i", f"testsrc=size=640x360:rate=25:duration={duration:.3f}",
        "-i", str(voice_wav),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stderr[-800:])
        raise SystemExit(f"ffmpeg failed building sample: exit {proc.returncode}")

    meta = video_service.get_video_metadata(out, settings)
    print(f"[make] sample ready: {out} duration={meta.duration:.2f}s has_audio={meta.has_audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
