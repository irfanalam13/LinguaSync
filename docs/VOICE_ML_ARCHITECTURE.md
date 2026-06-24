# VOICE_ML ARCHITECTURE

`Voice_ML` is the dedicated inference service. It owns **all** ML execution; the
backend reaches it only over HTTP.

## Service map
```
                     HTTP (httpx)
Voice_backend  ───────────────────────▶  Voice_ML  (FastAPI, port 8001)
 (port 8000)     POST /ml/v1/translate     │
                                           ▼
                              pipelines/translation_pipeline.run_pipeline
                                           │
        ┌──────────────┬───────────────────┼───────────────────┬───────────────┐
        ▼              ▼                   ▼                   ▼               ▼
   video_service  transcription_     translation_         tts_service     (Phase 2)
   (ffmpeg)       service            service              MMS / SpeechT5  voice_preservation_service
                  faster-whisper     NLLB-200                              + speaker_embedding_service
                                                                          + similarity_service
```

## Package layout (`Voice_ML/app/`)
| Module | Responsibility |
|--------|----------------|
| `main.py` | FastAPI service: `/ml/v1/health`, `/ml/v1/translate` |
| `core/` | `config` (models, device, paths, ffmpeg), `device`, `exceptions`, `logging` (StageTimer) |
| `services/transcription_service.py` | faster-whisper (+whisper fallback), lazy, auto-detect, segments |
| `services/translation_service.py` | NLLB-200, en↔ne, anti-repetition decoding + chunking |
| `services/tts_service.py` | base TTS — MMS-TTS (en) / SpeechT5+HiFi-GAN (ne), engine-agnostic |
| `services/video_service.py` | ffmpeg extract / replace / probe / validate (safe argv) |
| `services/speaker_embedding_service.py` | **(Phase 2)** extract source speaker timbre embedding |
| `services/voice_preservation_service.py` | **(Phase 2)** OpenVoice tone-color conversion onto base TTS |
| `services/similarity_service.py` | **(Phase 2)** Resemblyzer cosine similarity (source vs output) |
| `pipelines/translation_pipeline.py` | base pipeline: extract→ASR→translate→TTS→mux + timings + artifacts |
| `pipelines/speaker_preservation_pipeline.py` | **(Phase 2)** wraps base + embedding→conversion→similarity |
| `schemas/pipeline.py` | ML-internal pydantic models (re-exports shared LANGUAGES/StageTimings) |
| `cli/main.py` | local CLI driver for the pipeline |
| `models/` | model wrapper/loader helpers |

## Contracts (`shared/`)
- `languages.py` — `LANGUAGES` (en, ne + NLLB codes).
- `contracts.py` — `MLTranslateRequest`, `MLTranslateResponse`, `StageTimings`
  (now includes `voice_conversion`).
- `logging.py` — generic console + rotating-JSON logging used by both services.

## Lazy loading
Every model (whisper, NLLB, MMS, SpeechT5, and Phase-2 OpenVoice/Resemblyzer) is a
lazy singleton — imported/downloaded only on first use, so the service starts instantly
and unit tests run with no ML stack.

## Isolation
`Voice_ML` runs in its own environment (uv venv, Python 3.12) so its heavier/older
Phase-2 deps (OpenVoice) never touch the backend or the validated Phase 1 stack.

## Phase 2 data flow (speaker preservation)
```
source audio ──► speaker_embedding_service  ──► speaker embedding (temp/speaker/)
translated text ──► tts_service (base voice, target lang) ──► base.wav
base.wav + embedding ──► voice_preservation_service (OpenVoice ToneColorConverter) ──► preserved.wav
similarity_service(source audio, preserved.wav) ──► {"similarity": 0.xx}  (target > 0.70)
preserved.wav ──► video_service.replace_audio ──► output.mp4
```
