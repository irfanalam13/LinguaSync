"""Command-line entry point for the translation pipeline.

Usage::

    python -m app.cli.main input.mp4 --target ne
    python -m app.cli.main input.mp4 --target en --source ne

Exit codes: 0 success, 2 bad usage / pipeline error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import PipelineError
from app.core.logging import configure_logging
from app.schemas.pipeline import LANGUAGES
from app.pipelines import (
    cloning_pipeline,
    localization_pipeline,
    speaker_preservation_pipeline,
    translation_pipeline,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voice-converter",
        description="Translate the spoken audio of a video (English <-> Nepali).",
    )
    parser.add_argument("input", help="Path to the input video (e.g. input.mp4)")
    parser.add_argument(
        "--target", "-t", required=True, choices=sorted(LANGUAGES),
        help="Target language: en or ne",
    )
    parser.add_argument(
        "--source", "-s", default=None, choices=sorted(LANGUAGES),
        help="Force source language (default: auto-detect)",
    )
    parser.add_argument("--job-id", default=None, help="Optional job id (default: random)")
    parser.add_argument(
        "--preserve-voice", action="store_true",
        help="Phase 2: preserve the original speaker's voice (OpenVoice, single ref)",
    )
    parser.add_argument(
        "--clone-voice", action="store_true",
        help="Phase 3: clone the speaker's identity (OpenVoice multi-reference profile)",
    )
    parser.add_argument(
        "--speaker-sample", default=None,
        help="Phase 3: optional separate speaker enrollment clip (default: source audio)",
    )
    parser.add_argument(
        "--localize", action="store_true",
        help="Phase 4: full localization — clone voice + Wav2Lip lip-sync",
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output")
    return parser


def _force_utf8_stdio() -> None:
    """Windows consoles default to cp1252 and choke on '✓'/'•'/Devanagari.

    Reconfigure stdio to UTF-8 so progress/output never crashes on encoding.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    args = build_parser().parse_args(argv)
    settings = get_settings()
    settings.ensure_dirs()
    configure_logging(settings.logs_dir)

    if not Path(args.input).exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    def progress(msg: str) -> None:
        if not args.quiet:
            print(f"  • {msg}", file=sys.stderr)

    try:
        if args.localize:
            result = localization_pipeline.run_pipeline(
                video_path=args.input,
                target_language=args.target,
                source_language=args.source,
                job_id=args.job_id,
                settings=settings,
                progress=progress,
                speaker_sample=args.speaker_sample,
            )
        elif args.clone_voice:
            result = cloning_pipeline.run_pipeline(
                video_path=args.input,
                target_language=args.target,
                source_language=args.source,
                job_id=args.job_id,
                settings=settings,
                progress=progress,
                speaker_sample=args.speaker_sample,
            )
        else:
            runner = (
                speaker_preservation_pipeline.run_pipeline
                if args.preserve_voice
                else translation_pipeline.run_pipeline
            )
            result = runner(
                video_path=args.input,
                target_language=args.target,
                source_language=args.source,
                job_id=args.job_id,
                settings=settings,
                progress=progress,
            )
    except PipelineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    t = result.timings
    print("\n✓ Translation complete")
    print(f"  job id        : {result.job_id}")
    print(f"  direction     : {result.source_language} -> {result.target_language}")
    print(f"  output video  : {result.output_video}")
    print(f"  artifacts     : {result.artifacts_dir}")
    if result.preserve_voice:
        mode = "LOCALIZED (clone+lipsync)" if args.localize else (
            "CLONED" if args.clone_voice else "PRESERVED")
        print(f"  voice         : {mode}  | speaker similarity = {result.similarity}")
    print(
        f"  timings (s)   : extract={t.audio_extraction} asr={t.transcription} "
        f"translate={t.translation} tts={t.tts} voice_conv={t.voice_conversion} "
        f"lip_sync={t.lip_sync} render={t.video_render} total={t.total}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
