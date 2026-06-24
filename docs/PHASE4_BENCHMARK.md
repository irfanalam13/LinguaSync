# PHASE 4 BENCHMARK

> Real measurements, isolated `Voice_ML/.venv`, **CPU only** (no GPU present).
> Run date: 2026-06-24. Stage times from `core.logging.StageTimer`.

## NE → EN full localization (`p4_ne2en`, 11.5 s real human clip) — measured

| Stage | Seconds | Notes |
|-------|--------:|-------|
| Audio extraction | 0.055 | ffmpeg |
| Transcription | 17.515 | faster-whisper **small** |
| Translation | 32.674 | NLLB-200 |
| Base TTS | 14.448 | MMS English |
| Voice cloning | 22.128 | speaker profile (multi-ref) + OpenVoice convert |
| **Lip sync (Wav2Lip)** | **126.508** | s3fd per-frame + GAN, 270 px / 20 fps |
| Video render | 0.252 | ffmpeg mux |
| **Total** | **213.580** | ~3.5 min end-to-end |

## EN → NE lip-sync stage (`p4_en2ne`) — measured
- Wav2Lip lip-sync (real face + Nepali cloned audio, 270 px): **50.7 s** (4.16 s output).
- (Translate+clone audio reused from the measured Phase-3 `p3_en2ne` run: ~57 s.)

## Resource usage
- **CPU:** all inference CPU-bound; lip-sync (per-frame s3fd + Wav2Lip GAN) is the dominant
  cost (~60% of NE→EN wall time). No multithreading tuning applied.
- **GPU:** none available on this host → **not used** (`device=cpu`). The code auto-selects
  CUDA when present (`core.device`); GPU would cut ASR/TTS/clone/lip-sync several-fold and
  make full-resolution lip-sync feasible.
- **Memory:** not instrumented to exact peak RSS. Resident models when localizing:
  faster-whisper small (~0.5–1 GB), NLLB-600M (~2.4 GB), MMS/SpeechT5, OpenVoice converter
  (~0.2 GB), Wav2Lip + s3fd (~0.5 GB), Resemblyzer/ECAPA — summed model footprint is
  **~4–5 GB**; observed comfortably within the host's RAM (no swapping/OOM). *(Exact
  per-stage RSS was not profiled — stated as an honest estimate, not a measured peak.)*
- **Disk:** vendored Wav2Lip checkpoints ~0.5 GB; HF model cache shared (~3–4 GB, one-time).

## Levers for speed
- GPU (largest win), smaller ASR model where Nepali accuracy allows, lower `lipsync_fps`,
  trimming via `VC_LIPSYNC_MAX_SECONDS`, and caching the loaded s3fd via `model_manager`
  (already done) to avoid reloads across requests.
