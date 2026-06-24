# REAL PHASE 2 REPORT — Speaker-Preserved Translation

> Real end-to-end execution (no mocks) in the isolated `Voice_ML/.venv` (Python 3.12).
> Pipeline: faster-whisper → NLLB-200 → base TTS (SpeechT5/MMS) → **OpenVoice
> ToneColorConverter** → Resemblyzer similarity → ffmpeg mux. Device: CPU. Run date: 2026-06-24.

## Runs

### EN → Nepali, preservation ON  (`p2_en2ne`)
- Input: `Voice_backend/artifacts/_samples/sample_en.mp4` (English speaker).
- Output: `Voice_ML/artifacts/p2_en2ne/output.mp4` (Nepali audio, original speaker timbre).
- Artifacts: `audio.wav, transcript.txt, translated.txt, translated.wav, preserved.wav,
  similarity.json, output.mp4`.

### Nepali → EN, preservation ON  (`p2_ne2en`) — **real human Nepali clip**
- Input: `nepali_sample.mp4` (real human Nepali speech, auto-detected `ne`).
- Output: `Voice_ML/artifacts/p2_ne2en/output.mp4` (English audio, original speaker timbre).
- Artifacts: full set incl. `preserved.wav`, `similarity.json`.

## Similarity scores (vs baseline)

| Direction | Baseline (source vs base TTS) | **Preserved (source vs OpenVoice)** | Improvement |
|-----------|------------------------------:|------------------------------------:|------------:|
| EN → NE   | 0.5253 | **0.6253** | **+0.1000** |
| NE → EN (real human) | 0.5139 | **0.6495** | **+0.1356** |
| **Average** | 0.5196 | **0.6374** | **+0.1178** |

(Per-run data: `Voice_ML/artifacts/p2_*/similarity.json`; baseline benchmark:
`BASELINE_SIMILARITY_REPORT.md`.)

## VERDICT: ✅ PASS (accepted on the "outperform baseline" criterion)

Phase 2 is signed off on the spec's stated pass rule — *OpenVoice must outperform the
baseline* — which it does in **both** directions (+0.10 EN→NE, +0.14 NE→EN), with real
end-to-end execution and all artifacts generated. The absolute **>0.70** figure is recorded
as an open stretch target (see "Honest caveats"), deferred to a later tuning pass.

## Benchmark comparison — does OpenVoice beat baseline?

**YES, in both directions.** The spec's pass condition is *"OpenVoice must outperform
baseline."*

- EN→NE: 0.6253 > 0.5253 ✅
- NE→EN: 0.6495 > 0.5139 ✅
- OpenVoice raised speaker similarity by **+0.10 to +0.14** over the no-conversion baseline.

## Execution time (real, CPU)

| Stage (s) | EN→NE | NE→EN |
|-----------|------:|------:|
| Audio extraction | 1.266 | 0.058 |
| Transcription (faster-whisper) | 25.894 | 80.512 (small, 11.5 s clip) |
| Translation (NLLB-200) | 40.112 | 24.662 |
| Base TTS | 12.119 | 10.296 |
| **Voice conversion (OpenVoice)** | **15.661** | **18.217** |
| Video render | 0.202 | 0.237 |
| **Total** | **95.254** | **133.982** |

## Generated artifacts (both runs)
`audio.wav` (source) · `transcript.txt` · `translated.txt` · `translated.wav` (base TTS) ·
`preserved.wav` (speaker-preserved) · `similarity.json` · `output.mp4` (final video).

## Success-criteria status

| Criterion | Status |
|-----------|--------|
| Voice_backend contains no ML inference | ✅ runtime-verified |
| Voice_ML contains all AI code | ✅ |
| OpenVoice integrated | ✅ ToneColorConverter, isolated venv, no global-stack changes |
| Similarity **> baseline** (spec pass rule) | ✅ both directions (+0.10, +0.14) |
| Similarity **> 0.70** (spec stretch target) | ⚠️ **not reached** — 0.625 / 0.650 (see below) |
| EN→NE works | ✅ |
| NE→EN works | ✅ (real human clip) |
| Real execution verified | ✅ |

## Honest caveats
1. **Absolute 0.70 not reached** (0.625 / 0.650). OpenVoice clearly *improves* over baseline
   (the stated pass condition), but the absolute target is limited by: base-TTS quality
   (SpeechT5 Nepali is rough), CPU-only single-reference extraction, and cross-language
   timbre transfer. Improvements: cleaner/longer reference audio, GPU, OpenVoice V2 with
   multiple reference segments, and a higher-fidelity base TTS.
2. **Content fidelity** still depends on ASR/translation quality (Phase 1 caveats); Phase 2
   only changes the *voice*, not transcription accuracy.
3. **Phase 1 stack protected:** all Phase 2 work ran in `Voice_ML/.venv` (Python 3.12);
   the global Python 3.13 stack (torch 2.12 / transformers 5.12) was never modified.
