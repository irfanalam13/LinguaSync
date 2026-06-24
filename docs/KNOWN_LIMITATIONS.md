# KNOWN LIMITATIONS

Honest, project-wide limitations as of Phase 4. None are hidden; each has a cause and a
mitigation/escalation path.

## Lip sync (Phase 4)
- **Single speaker only.** Face detection reports a single primary face per frame. Multiple
  speakers, face switching, speaker tracking, and scene changes are **stretch goals, not
  implemented** (and explicitly out of Phase 4 acceptance scope).
- **CPU performance.** Wav2Lip is per-frame s3fd + GAN; the input is downscaled to 270 px /
  20 fps for tractable CPU runtime (~127 s for an ~11 s clip). Full-resolution / long videos
  need a GPU.
- **Whole-frame face requirement.** Wav2Lip aborts if a frame has no detectable face; real
  clips have brief turns/occlusions. Patched to reuse the last valid box, but heavy
  occlusion / profile shots still degrade quality. Long clips are trimmed for CPU runtime
  (the genuine EN→NE demo used a 12 s segment of the 35 s `english_sample.mp4`).
- **Perceptual quality not auto-verified.** Lip-sync realism must be confirmed by human
  playback; downscaling and a non–studio base TTS reduce sharpness.
- **Wav2Lip is a 2020 codebase** vendored and patched (old librosa API, `np.int`, Windows
  `shell`/PATH/encoding). Patches live in the gitignored `Voice_ML/Wav2Lip/` and are listed
  in `REAL_PHASE4_REPORT.md`.

## Voice cloning / preservation (Phases 2–3)
- **Cross-language speaker similarity is moderate.** Resemblyzer (primary): EN→NE 0.60,
  NE→EN 0.675; SpeechBrain ECAPA scores cross-language pairs near zero (out of regime) and is
  a non-gating secondary metric (per `PHASE3_ACCEPTANCE_DECISION.md`). The 0.75+ target is a
  future stretch goal.
- **Short enrollment.** Samples were 5–11 s (1–2 reference segments), not the ideal 30 s →
  weaker multi-reference voiceprint.
- **OpenVoice = timbre transfer**, not full identity (cadence/prosody/idiolect) cloning.

## Translation / ASR (Phase 1)
- **Nepali ASR** with whisper `base` is weak; `small`+ recommended (used in later phases).
  Auto-detect can misfire on degraded/synthetic Nepali audio.
- **NLLB** can degenerate on long unpunctuated ASR text → mitigated with
  `no_repeat_ngram_size`/`repetition_penalty` + chunking.
- **Two languages only** (en ⇄ ne).

## TTS
- **No Nepali in MMS-TTS** → Nepali uses a community **SpeechT5** model (intelligible, not
  studio-grade). English uses MMS-TTS.

## Platform / environment
- **CPU-only host**; GPU auto-enabled if present but untested here.
- **Windows specifics** handled: ffmpeg static build off-PATH, cp1252 console encoding,
  symlink-privilege (SpeechBrain `COPY` strategy), float-WAV → PCM-16.
- **Python 3.12 isolated venv** for all Phase 2–4 ML; the validated Phase 1 global 3.13 stack
  is never modified.
- **Synchronous processing**; no queue/concurrency (intentional for MVP).

## Metrics
- ECAPA cross-language scores are unreliable as an absolute gate; Resemblyzer is the primary
  similarity metric. Exact peak memory was estimated, not profiled.
