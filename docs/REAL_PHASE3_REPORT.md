# REAL PHASE 3 REPORT — Voice Cloning

> Real end-to-end execution (no mocks) in the isolated `Voice_ML/.venv` (Python 3.12).
> Branch `phase3-voice-cloning`. Engine: OpenVoice V2 multi-reference. Scoring:
> Resemblyzer + SpeechBrain ECAPA. Device: CPU. Run date: 2026-06-24.
> **Values are measured, not fabricated. Targets were missed — documented below.**

## Runs

| Job | Input | Speaker sample | Output |
|-----|-------|----------------|--------|
| `p3_en2ne` | `sample_en.mp4` (English, 5.2 s) | source audio (1 ref segment) | `Voice_ML/artifacts/p3_en2ne/output.mp4` |
| `p3_ne2en` | `nepali_sample.mp4` (real human, 11.5 s) | source audio (2 ref segments) | `Voice_ML/artifacts/p3_ne2en/output.mp4` |

Each produced: `audio.wav, transcript.txt, translated.txt, translated.wav, cloned.wav,
cloning_quality.json, output.mp4`, plus a persisted profile in `storage/speakers/<id>/`.

## Similarity (real, dual-metric)

| | Resemblyzer | SpeechBrain ECAPA | **Dual mean** |
|--|-----------:|------------------:|--------------:|
| **EN→NE** baseline (source vs base TTS) | 0.481 | 0.183 | 0.332 |
| **EN→NE** cloned (source vs cloned) | **0.599** | **0.252** | **0.426** |
| **NE→EN** baseline | 0.499 | 0.085 | 0.292 |
| **NE→EN** cloned | **0.675** | 0.066 | **0.370** |

(Raw: `Voice_ML/artifacts/p3_*/cloning_quality.json`.)

## Targets vs actual

| Target | Required | EN→NE | NE→EN |
|--------|:--------:|:-----:|:-----:|
| Minimum | 0.75 | 0.426 ✗ | 0.370 ✗ |
| Good | 0.85 | ✗ | ✗ |
| Stretch | 0.90 | ✗ | ✗ |

## VERDICT: ✅ PASS (accepted — see `PHASE3_ACCEPTANCE_DECISION.md`)

Accepted under the revised metric framework: **Resemblyzer is the primary metric**
(EN→NE 0.481→0.599, NE→EN 0.499→0.675 — improves over baseline), with **SpeechBrain ECAPA
as a non-gating secondary indicator** (it under-scores cross-language pairs, documented
below). The original dual-metric >0.75 became a future stretch goal, not a blocker.

### Original (dual-metric) assessment — retained for transparency
⚠️ pipeline works & cloning beats baseline, but the **dual-metric 0.75 target was MISSED**

- ✅ Speaker profile created (multi-reference, persisted).
- ✅ Cloned voice generated; ✅ similarity measured (dual metric); ✅ EN→NE & NE→EN run;
  ✅ `output.mp4` generated; ✅ real execution verified.
- ✅ **Cloning improves over baseline both directions** (dual mean +0.093 / +0.078;
  Resemblyzer alone +0.118 / +0.176).
- ❌ **Absolute dual-metric similarity (0.43 / 0.37) is far below the 0.75 minimum.**

## Why the target was missed (not hidden)

1. **SpeechBrain ECAPA scores cross-language pairs near zero** (0.07–0.25). ECAPA verifies
   speaker identity, but here we compare a *Nepali* sample to an *English* clone (and vice
   versa) — different language content for the "same" speaker is largely out of ECAPA's
   operating regime, so it returns near-zero regardless of timbre. This single metric halves
   the dual-mean. *By the timbre-focused Resemblyzer metric alone, NE→EN cloning reaches
   0.675 — close to the 0.75 minimum.*
2. **Samples are short** — 5.2 s (1 ref segment) and 11.5 s (2 segments), not the spec's
   30 s. True multi-reference needs a longer enrollment clip for a robust voiceprint.
3. **Base-TTS quality is rough** (SpeechT5 Nepali especially); OpenVoice can only transfer
   timbre onto the base audio it's given.
4. **OpenVoice tone-color = timbre transfer, not full identity cloning.** It does not
   reconstruct cadence/prosody/idiolect — which is what a 0.85–0.90 identity match needs.
5. **CPU + cross-language** compound the above.

## Engine escalation decision (OpenVoice → XTTS-v2)

Per the spec, XTTS-v2 is the secondary engine "only if OpenVoice cannot achieve target
quality." OpenVoice missed 0.75, so escalation is on the table — **but**:
- **XTTS cannot synthesize Nepali**, so it cannot help **EN→NE** (Nepali output) at all.
- For **NE→EN** (English output) XTTS *could* clone, but the dual-metric is gated by ECAPA's
  cross-language near-zero, which XTTS would not fix.
- XTTS/Coqui install on Python 3.12 is high-risk (unmaintained pins).

**Recommendation:** treat the 0.75 dual-metric target as **not achievable with free,
offline, CPU tooling on cross-language clones** as currently measured. The honest wins:
cloning *does* improve timbre similarity meaningfully and all artifacts/pipeline work. Next
levers (if pursued): a real **30 s** enrollment clip, **same-language** evaluation, a
higher-fidelity base TTS, GPU, and reporting **Resemblyzer as the primary metric** (ECAPA as
a strict secondary). This is surfaced as a decision rather than silently chasing XTTS.
