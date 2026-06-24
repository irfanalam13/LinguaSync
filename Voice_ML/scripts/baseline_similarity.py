"""Baseline speaker-similarity benchmark (no voice conversion).

Measures cosine similarity between the ORIGINAL speaker (extracted source audio) and
the BASE TTS output (SpeechT5 Nepali / MMS English) for each direction. This is the
benchmark that OpenVoice voice preservation must improve upon.

Run inside the isolated venv:
    Voice_ML/.venv/Scripts/python.exe -m scripts.baseline_similarity
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings
from app.services import similarity_service

REPO = Path(__file__).resolve().parents[2]

CASES = {
    "en_to_ne": REPO / "Voice_backend" / "artifacts" / "real_en2ne",
    "ne_to_en": REPO / "Voice_backend" / "artifacts" / "real_ne2en_human",
}


def main() -> int:
    settings = get_settings()
    results = {}
    for name, art in CASES.items():
        source = art / "audio.wav"        # original speaker
        base_tts = art / "translated.wav"  # base TTS output (no preservation)
        if not source.exists() or not base_tts.exists():
            results[name] = {"error": f"missing artifacts in {art}"}
            continue
        sim = similarity_service.compare_audio(source, base_tts, settings)["similarity"]
        results[name] = {
            "source_audio": str(source),
            "base_tts_audio": str(base_tts),
            "baseline_similarity": sim,
        }

    vals = [r["baseline_similarity"] for r in results.values() if "baseline_similarity" in r]
    summary = {
        "cases": results,
        "average_baseline_similarity": round(sum(vals) / len(vals), 4) if vals else None,
    }
    out = REPO / "Voice_ML" / "artifacts" / "baseline_similarity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
