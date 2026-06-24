# VOICE CLONING REPORT (Phase 3)

## Approach

Phase 3 clones a speaker's **identity** onto translated speech, going beyond Phase 2's
single-reference timbre preservation:

```
speaker sample (≤30s) ─► speaker_profile_service
                          ├─ Resemblyzer d-vector            → embedding.npy
                          ├─ OpenVoice MULTI-REFERENCE SE     → se.pth   (segments averaged)
                          └─ pitch / energy / speaking-rate   → profile.json
translated text ─► base TTS ─► voice_clone_service (OpenVoice convert to profile SE) ─► cloned.wav
cloned.wav vs sample ─► quality_evaluation_service (Resemblyzer + SpeechBrain ECAPA)
cloned.wav ─► mux ─► output.mp4
```

Persisted under `Voice_ML/storage/speakers/<speaker_id>/` (`profile.json`,
`embedding.npy`, `se.pth`).

## Engine

- **Primary: OpenVoice V2, multi-reference.** `extract_se()` is fed *multiple* segments of
  the sample and averages their tone-color embeddings — a richer voiceprint than Phase 2's
  single reference. Reused via `voice_preservation_service.extract_se_multi` /
  `convert_with_se` (no duplication).
- **Secondary: XTTS-v2** — *not* integrated (see "Engine escalation").
- **Fish Speech** — not installed (per spec, only if OpenVoice + XTTS both fail).

## Speaker profile contents (real example, `p3_ne2en`)
```json
{ "speaker_id": "spk_84d9332b94", "num_reference_segments": 2,
  "duration_s": 11.x, "pitch": {"mean_hz": ...}, "energy": {...},
  "speaking_rate_per_s": ..., "embedding_path": ".../embedding.npy", "se_path": ".../se.pth" }
```

## Results (real, dual-metric)

| Direction | Resemblyzer base→clone | SpeechBrain base→clone | Dual-mean clone | Target 0.75 |
|-----------|-----------------------:|-----------------------:|----------------:|:-----------:|
| EN → NE   | 0.481 → **0.599** | 0.183 → **0.252** | **0.426** | ✗ |
| NE → EN   | 0.499 → **0.675** | 0.085 → 0.066 | **0.370** | ✗ |

- **Cloning improves the timbre (Resemblyzer) metric substantially** (+0.12 / +0.18); NE→EN
  reaches **0.675** by Resemblyzer alone (near the 0.75 minimum).
- The **dual-metric mean misses 0.75** — dragged down by SpeechBrain ECAPA (see
  `REAL_PHASE3_REPORT.md` for the full why).

## Engine escalation (OpenVoice → XTTS)
The spec says attempt XTTS-v2 if OpenVoice misses target. **XTTS cannot speak Nepali**, so
it cannot help the EN→NE (Nepali-output) direction at all, and for NE→EN it is unlikely to
fix the ECAPA cross-language score. XTTS install on Python 3.12 is also high-risk. This is
flagged as a decision point rather than silently attempted — see `REAL_PHASE3_REPORT.md`.
