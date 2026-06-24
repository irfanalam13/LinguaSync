# PHASE 3 — Analysis (Real Voice Cloning)

> Branches: `phase2-complete` (recoverable checkpoint at the Phase-2 commit) and
> `phase3-voice-cloning` (this work). Phases 1 & 2 are authoritative and untouched.

## Objective vs Phase 2

| | Phase 2 (preservation) | Phase 3 (cloning) |
|--|------------------------|-------------------|
| Goal | preserve *characteristics* (gender/pitch/energy) | clone *identity* (voiceprint, cadence, timbre) |
| Reference | single utterance, single SE | **30-s sample, multi-reference SE** |
| Engine | OpenVoice ToneColorConverter (1 ref) | OpenVoice V2 **multi-reference** (then XTTS if needed) |
| Profile | none (ephemeral) | persisted `storage/speakers/<id>/{profile.json,embedding.npy}` |
| Scoring | Resemblyzer cosine | Resemblyzer **+ SpeechBrain ECAPA** |

## What Phase 3 reuses (no duplication)
- `translation_pipeline` (extract→ASR→translate→base TTS→mux) — unchanged.
- `voice_preservation_service` (OpenVoice converter load + convert) — reused; cloning adds
  **multi-reference SE extraction** on top.
- `similarity_service` (Resemblyzer cosine), `video_service`, `core`, `shared`.
- Backend/ML split, isolated `Voice_ML/.venv` (Python 3.12). No backend ML.

## New modules
- `services/speaker_profile_service.py` — build & persist a speaker profile from a
  ≤30-s sample: Resemblyzer embedding, **multi-reference OpenVoice SE**, pitch (F0 via
  librosa pyin), energy (RMS), speaking rate.
- `services/voice_clone_service.py` — synthesize translated text in target language (base
  TTS) then apply the profile's multi-reference SE via OpenVoice → cloned voice.
- `services/quality_evaluation_service.py` — Resemblyzer + (optional) SpeechBrain ECAPA
  similarity → `{"similarity": x, ...}`.
- `pipelines/cloning_pipeline.py` — orchestrates profile → translate → clone → score → mux.

## Engine strategy (per spec)
1. **OpenVoice V2 multi-reference** first — segment the 30-s sample into chunks and average
   their SEs (`extract_se([seg1, seg2, ...])`) for a richer voiceprint than Phase 2's single ref.
2. **XTTS-v2** only if OpenVoice can't reach target quality. Isolated; never touches the
   protected stack. (XTTS *does* clone, but cannot speak Nepali — so for the Nepali leg it
   would only help the English-target direction.)
3. **Fish Speech** — not installed unless 1 & 2 both fail.

## Targets (record actuals; do not fabricate)
- Min **0.75**, good **0.85**, stretch **0.90** similarity.
- Phase 2's OpenVoice single-ref reached ~0.63–0.65. Multi-reference should help, but **0.75+
  on CPU with rough base TTS is uncertain** — honest expectation: it may fall short, which
  will be documented (not hidden) in `REAL_PHASE3_REPORT.md` with the reasons and the XTTS
  escalation decision.

## Risks
- SpeechBrain needs `torchaudio` matching torch 2.12.1 — if it won't resolve, scoring falls
  back to Resemblyzer-only (documented).
- Higher absolute similarity is gated by base-TTS fidelity + CPU; the levers are multi-ref,
  longer/cleaner samples, and (if needed) XTTS for the English target.
