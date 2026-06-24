# BENCHMARK REPORT — Phase 1 (real runs)

Real measurements (not estimates). Hardware: **CPU only** (no GPU), Windows 11,
Python 3.13. Models: faster-whisper `base`, NLLB-200-distilled-600M, MMS-TTS (en),
SpeechT5-Nepali + HiFi-GAN (ne). Timings captured by `core.logging.StageTimer` and
emitted in every `PipelineResult.timings`. Run date: 2026-06-24.

## Run 1 — English → Nepali (`sample_en.mp4`, 5.20 s input)

| Stage | Seconds | % of total |
|-------|--------:|-----------:|
| Audio extraction (ffmpeg) | 0.053 | 0.1% |
| Transcription (faster-whisper base) | 12.723 | 29.6% |
| Translation (NLLB-200) | 18.241 | 42.5% |
| TTS (SpeechT5 Nepali + HiFi-GAN) | 11.761 | 27.4% |
| Video render (ffmpeg mux) | 0.155 | 0.4% |
| **Total** | **42.933** | 100% |

## Run 2 — Nepali → English (real human clip `nepali_sample.mp4`, 11.49 s input)

faster-whisper **small** (stronger Nepali ASR than `base`); source language
**auto-detected** as `ne`.

| Stage | Seconds | % of total |
|-------|--------:|-----------:|
| Audio extraction (ffmpeg) | 0.243 | 0.3% |
| Transcription (faster-whisper small) | 40.798 | 44.4% |
| Translation (NLLB-200) | 40.117 | 43.7% |
| TTS (MMS-TTS English) | 10.429 | 11.3% |
| Video render (ffmpeg mux) | 0.299 | 0.3% |
| **Total** | **91.886** | 100% |

*(Supersedes an earlier synthetic-input attempt; using `small` instead of `base` and a
real clip roughly doubles ASR/translate time but yields correct language detection and a
coherent translation.)*

## Observations

- **ffmpeg stages are negligible** (<0.2 s); all cost is in the ML stages.
- **Translation (NLLB-600M) and transcription dominate** on CPU. The first call to each
  model in a process also pays a one-time load cost folded into these numbers.
- **TTS:** MMS-TTS (English, VITS) is ~2× faster than SpeechT5+HiFi-GAN (Nepali) for
  comparable text — single-pass VITS vs autoregressive SpeechT5 + vocoder.
- For a ~4–5 s clip, end-to-end ≈ **43 s on CPU**. This scales roughly linearly with
  audio length for ASR/TTS; translation scales with token count.

## Notes vs performance target

- Target was "≤ 5-minute video completes successfully." A 5 s clip takes ~43 s on CPU;
  extrapolating, a 5-minute clip is **minutes-scale on CPU** and would benefit greatly
  from a GPU (the device is auto-selected; CUDA would cut ASR/TTS several-fold).
- **Model download (first run only):** faster-whisper base, NLLB-600M (~2.4 GB), MMS-eng,
  SpeechT5-Nepali + HiFi-GAN — a one-time ~3–4 GB download, excluded from the timings above
  (models were warm/cached).
