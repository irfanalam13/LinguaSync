# PHASE 2 — Repository Analysis (Speaker-Preserved Translation)

> Read-only audit performed before any Phase 2 code. The repository is the
> post-Phase-1 codebase (clean `app/` package). **Phase 1's real end-to-end run is
> still in progress** (ML stack installing) — see "Sequencing risk" below.

## Existing Architecture (post-Phase 1)

```
Voice_backend/app/
  api/routes.py                  POST /api/v1/translate, GET /api/v1/health
  cli/main.py                    python -m app.cli.main input.mp4 --target ne
  core/                          config, logging (StageTimer), device, exceptions
  schemas/                       pydantic contracts (Transcription/Translation/TTS/Pipeline)
  services/
    video_service.py             ffmpeg (safe argv): extract/replace/probe/validate
    transcription_service.py     faster-whisper (+whisper fallback), lazy, auto-detect, segments
    translation_service.py       NLLB-200 (facebook/nllb-200-distilled-600M)
    tts_service.py               MMS-TTS (facebook/mms-tts-{eng,npi}), engine-agnostic interface
    pipeline.py                  orchestration + artifacts + per-stage timings
  utils/files.py                 job ids, per-job artifact dirs
  tests/                         44 mocked tests (green)
```

## What Phase 2 can REUSE as-is

| Phase 2 requirement | Already exists | Action |
|---------------------|----------------|--------|
| `transcription_service.py` (faster-whisper, EN/NE, auto-detect, timestamps) | ✅ exactly matches | **Reuse unchanged** |
| `translation_service.py` (EN↔NE) | ✅ via NLLB-200 | **Reuse** (see Argos note) |
| Structured logging + stage timers | ✅ `core/logging.py` | **Reuse** |
| `core/config.py`, exceptions, device detect | ✅ | **Reuse/extend** |
| FastAPI `POST /api/v1/translate` | ✅ | **Extend** with `preserve_voice` flag |
| CLI | ✅ `app/cli/main.py` | **Extend** with `--preserve-voice` |
| ffmpeg audio I/O | ✅ `video_service.py` | **Reuse** (also satisfies `audio_service` needs) |

Phase 2 is **mostly additive** — the heavy lifting (ASR, translation, video I/O,
config, logging, tests harness) is already done and reusable.

## Missing Modules (to add for Phase 2)

- `services/speaker_embedding_service.py` — extract speaker timbre/tone embedding from source audio.
- `services/voice_preservation_service.py` — synthesize translated text in the target language, then convert its timbre to the source speaker.
- `services/audio_service.py` — audio helpers (resample, segment-concat, duration) thin over ffmpeg. *(Note: `video_service` already covers extract/probe; `audio_service` will hold the new audio-only ops to avoid duplication.)*
- `app/models/` — model wrapper/loader package (Phase 2 required dir; currently absent).
- `temp/speaker/` — speaker-embedding store.
- Tests: `test_speaker_embedding.py`, `test_voice_preservation.py` (others already exist).

## Problems / Technical Debt relevant to Phase 2

1. No `app/models/` package yet (Phase 2 requires it).
2. `tts_service` is single-speaker; speaker preservation is a **new layer on top**, not a change to it — keep tts_service as the "base voice" generator and add a tone-color conversion stage.
3. No speaker-similarity metric anywhere (Phase 2 needs a >70% similarity score).

## Unused / Duplicate Code

- None introduced in Phase 1 (dead Celery/old services were already deleted). No duplication found. `audio_service` must be scoped carefully to **not duplicate** `video_service`'s ffmpeg helpers — it will call into them / share `_run`.

## Technology Feasibility — HONEST assessment (Python 3.13, offline)

The Phase 2 priority list (OpenVoice → XTTS-v2 → CosyVoice → Whisper) and "Argos
Translate" have real install/feasibility issues on this environment. Findings:

| Tech | Verdict | Reason |
|------|---------|--------|
| **Argos Translate (EN↔NE)** | ⚠️ High risk | Argos's offline package index has limited Nepali coverage; a direct `en↔ne` package may not exist (would force pivot translation or fail). NLLB-200 (already integrated) **does** support Nepali well. Recommend **keeping NLLB**, mirroring the approved Phase-1 TTS deviation. |
| **XTTS-v2 / Coqui `TTS`** | ⚠️ Likely won't install | The `TTS` package is unmaintained and not built for py3.13; also **cannot speak Nepali**. The maintained `coqui-tts` fork is unverified on 3.13. |
| **OpenVoice** | ✅ Usable (with care) | OpenVoice's **ToneColorConverter** is language-agnostic: it transfers a reference speaker's timbre onto *any* base-TTS audio. Pairing it with our **MMS-TTS** Nepali/English base gives speaker-preserved Nepali — the only free/local path that actually speaks Nepali *and* preserves the speaker. Dependency pinning vs our torch is the main risk. |
| **CosyVoice** | ⚠️ Heavy | Large deps, multilingual but Nepali support unclear; keep as fallback only. |
| **faster-whisper** | ✅ Already integrated | Reuse. |

### Recommended Phase 2 design (free, local, Nepali-capable)

```
source audio ──► speaker_embedding_service (OpenVoice tone-color extractor)
                                   │  speaker embedding (stored temp/speaker/)
translated text ──► tts_service (MMS-TTS, target lang)  ──► base voice wav
                                   │                              │
                                   └──► voice_preservation_service ◄┘
                                        (OpenVoice ToneColorConverter)
                                   │
                                   ▼  speaker-preserved wav
                       similarity = cosine(embed(source), embed(output))   (target >70%)
```

This **reuses** transcription, translation, MMS-TTS, ffmpeg, logging, config — and
**adds** only the embedding + conversion + similarity layers.

## Sequencing Risk (must resolve before coding)

1. **Phase 1 is not yet closed out.** The real EN→NE / NE→EN runs and
   `REAL_ACCEPTANCE_REPORT.md` are pending the ML install that is **currently running**.
2. **Dependency-conflict hazard.** Installing OpenVoice (and especially Coqui/XTTS) tends
   to **pin/downgrade torch & transformers**, which can break the Phase-1 stack mid-install.
   These should not be installed until the Phase-1 stack is verified, ideally in an isolated
   environment or pinned compatibly.

**Recommendation:** finish and verify Phase 1's real end-to-end runs first (the install is
the shared long pole and is already underway), then layer Phase 2 on top. Proceeding with
Phase 2 installs *now* risks invalidating Phase 1 before it's proven.
