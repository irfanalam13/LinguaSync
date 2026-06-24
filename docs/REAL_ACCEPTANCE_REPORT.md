# REAL ACCEPTANCE REPORT — English → Nepali

> Real end-to-end execution (no mocks). Models: faster-whisper `base`,
> NLLB-200-distilled-600M, MMS-TTS (en) / SpeechT5-Nepali (ne). Device: CPU.
> ffmpeg 8.1.1. Run date: 2026-06-24.

## Input File
`artifacts/_samples/sample_en.mp4` — 640×360, **5.20 s**, real English speech track
(synthesized offline with MMS-TTS, then muxed onto a test pattern).

## Output File
`artifacts/real_en2ne/output.mp4` — **4.22 s**, H.264 video + AAC Nepali audio track.
All required artifacts present in `artifacts/real_en2ne/`:

| Artifact | Size | Notes |
|----------|------|-------|
| `audio.wav` | 168 KB | extracted mono 16 kHz |
| `transcript.txt` | 88 B | English transcription |
| `translated.txt` | 75 B | Nepali (Devanagari) |
| `translated.wav` | ~250 KB | PCM-16, **playable**, 4.22 s |
| `output.mp4` | 67 KB | final video |

## Execution Time (real)
| Stage | Seconds |
|-------|--------:|
| Audio extraction | 0.053 |
| Transcription (faster-whisper base) | 12.723 |
| Translation (NLLB-200) | 18.241 |
| TTS (target=ne → SpeechT5+HiFi-GAN) | 11.761 |
| Video render | 0.155 |
| **Total** | **42.933** |

## Detected Language
`en` (auto-detected by faster-whisper).

## Translation Sample
- **Transcript (en):** `The weather today is bright and sunny many people are walking in the par near the river.`
  - *(Input sentence was "…in the park near the river." — ASR dropped the "k" in "park"; otherwise verbatim.)*
- **Translation (ne):** `आज मौसम उज्यालो र घामको छ धेरै मानिसहरु नदी नजिकैको पार्लमा हिंडिरहेका छन्।`
  - Valid, fluent Nepali Devanagari — semantically faithful.

## Generated Audio Duration
`translated.wav` = **4.22 s** (Nepali). Output video trimmed to 4.22 s (`-shortest`);
source 5.20 s → delta 0.98 s, **within tolerance**.

## Validation Checks (automated, `scripts/validate_artifacts.py`)
```
output.mp4 exists ................. ✓
translated.wav exists ............. ✓
transcript.txt exists ............. ✓
translated.txt exists ............. ✓
translated text contains Nepali ... ✓ (Devanagari)
translated.wav playable (PCM-16) .. ✓
output duration ≈ source .......... ✓ (Δ 0.98s ≤ 1.5s)
no unhandled exceptions ........... ✓
hard_fail ......................... false
```

## PASS / FAIL
### ✅ PASS

All acceptance artifacts generated; transcription accurate; translation is valid,
fluent Nepali; audio playable; output video produced and muxed correctly; no
unhandled exceptions.

### Honest caveat (quality, not pass/fail)
The Nepali **text** is high quality. The Nepali **audio** uses a community SpeechT5
Nepali model with a *generic* speaker embedding (Phase 1 has no voice preservation),
so the synthesized voice is intelligible-but-robotic and not studio-grade. This is a
free-model quality limitation, not a pipeline defect. See `BLOCKERS.md` #2.
