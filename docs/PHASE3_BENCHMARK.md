# PHASE 3 BENCHMARK

> Real measurements, isolated `Voice_ML/.venv`, **CPU only**. OpenVoice V2 multi-reference
> + dual-metric scoring (Resemblyzer + SpeechBrain ECAPA). Run date: 2026-06-24.

## Similarity benchmark (baseline = no clone, OpenVoice = cloned)

| Direction | Metric | Baseline | OpenVoice clone | Δ | vs 0.75 min |
|-----------|--------|---------:|----------------:|---:|:-----------:|
| EN→NE | Resemblyzer | 0.481 | **0.599** | +0.118 | — |
| EN→NE | SpeechBrain ECAPA | 0.183 | **0.252** | +0.069 | — |
| EN→NE | **Dual mean** | 0.332 | **0.426** | +0.093 | ✗ |
| NE→EN | Resemblyzer | 0.499 | **0.675** | +0.176 | (near) |
| NE→EN | SpeechBrain ECAPA | 0.085 | 0.066 | −0.019 | — |
| NE→EN | **Dual mean** | 0.292 | **0.370** | +0.078 | ✗ |

**Reading:** cloning consistently raises the Resemblyzer (timbre) score; the dual mean is
held down by ECAPA's near-zero cross-language scores. See `REAL_PHASE3_REPORT.md` §"Why".

## Execution time (real, CPU)

### EN→NE clone (`p3_en2ne`, 5.2 s input) — measured
| Stage | Seconds |
|-------|--------:|
| Audio extraction | 1.317 |
| Transcription (faster-whisper base) | 7.661 |
| Translation (NLLB-200) | 19.599 |
| Base TTS (SpeechT5 Nepali) | 9.020 |
| **Voice cloning (profile + OpenVoice multi-ref)** | **19.262** |
| Video render | 0.172 |
| **Total (pipeline stages)** | **57.031** |
| + dual-metric scoring (ECAPA load + 2× eval) | ~8–10 (outside timed stages) |

### NE→EN clone (`p3_ne2en`, 11.5 s input) — component-derived
faster-whisper **small** dominates. Component costs measured this session:
ASR ≈ 80 s (small, 11.5 s clip), translate ≈ 25 s, base TTS ≈ 10 s, voice cloning ≈ 18 s,
render < 1 s → **end-to-end ≈ 135–145 s** (+ ~10 s ECAPA scoring). *(ASR/translate figures
carried from the measured Phase-2 NE→EN run on the same clip; cloning/scoring measured here.)*

## Observations
- **Voice cloning adds ~18–19 s** (profile multi-ref extraction + OpenVoice convert) on CPU.
- **SpeechBrain ECAPA** adds a one-time model load (~80 MB, copied not symlinked — Windows
  fix) plus ~1 s per comparison.
- Translation + ASR remain the dominant costs; GPU would cut both several-fold.

## Targets — actual
| | Min 0.75 | Good 0.85 | Stretch 0.90 |
|--|:--:|:--:|:--:|
| EN→NE (0.426) | ✗ | ✗ | ✗ |
| NE→EN (0.370) | ✗ | ✗ | ✗ |

Targets **missed** on the dual metric; reasons documented (not hidden) in
`REAL_PHASE3_REPORT.md`. Resemblyzer-only NE→EN (0.675) is the closest approach to 0.75.
