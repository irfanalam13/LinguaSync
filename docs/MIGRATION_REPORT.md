# MIGRATION REPORT — Phase 1 monolith → Phase 2 backend/ML split

## Goal
Separate the API gateway from ML inference: `Voice_backend` owns FastAPI/uploads/
jobs/status; `Voice_ML` owns ALL inference. No code duplication.

## New top-level layout
```
voice_converter/
├── Voice_backend/app/    api/ · core/ · db/ · jobs/ · schemas/ · tests/   (NO ML)
├── Voice_ML/app/         core/ · services/ · pipelines/ · schemas/ · models/ · cli/ · utils/ · tests/
├── shared/               languages.py · contracts.py · logging.py   (cross-service contract)
├── artifacts/  models/  docker/
```

## What moved (no duplication — files relocated, not copied)
| From (Voice_backend/app) | To | Notes |
|--------------------------|----|-------|
| `core/*` (config, device, exceptions, logging) | `Voice_ML/app/core/` | logging's generic parts lifted to `shared/logging.py`; `StageTimer` kept in ML |
| `services/*_service.py` + `__init__` | `Voice_ML/app/services/` | transcription, translation, tts, video |
| `services/pipeline.py` | `Voice_ML/app/pipelines/translation_pipeline.py` | renamed to a pipeline |
| `schemas/pipeline.py` | `Voice_ML/app/schemas/pipeline.py` | `LANGUAGES`/`StageTimings` now sourced from `shared` |
| `utils/*` | `Voice_ML/app/utils/` | |
| `cli/` | `Voice_ML/app/cli/` | drives the pipeline directly |
| `scripts/*` | `Voice_ML/scripts/` | sample-builder, validator |
| ML tests (`test_video_service/transcription/translation/tts/pipeline/cli`) | `Voice_ML/app/tests/` | `test_pipeline.py` → `test_translation_pipeline.py` |

## What is NEW
- `shared/`: `languages.py` (LANGUAGES), `contracts.py` (`MLTranslateRequest/Response`,
  `StageTimings`), `logging.py` (generic console/JSON setup). Single source of truth.
- `Voice_ML/app/main.py`: FastAPI inference service (`/ml/v1/health`, `/ml/v1/translate`).
- `Voice_backend/app/`: rebuilt as a gateway —
  - `core/config.py` (uploads, `ml_service_url`), `db/job_store.py` (status tracking),
    `jobs/ml_client.py` (httpx client to Voice_ML), `api/routes.py`
    (`/api/v1/translate`, `/api/v1/jobs/{id}`, `/api/v1/health`), `schemas/api.py`.

## Import strategy (avoids churn)
Both services keep their internal package named `app`, so existing `from app.…`
imports survived the move. A 6-line bootstrap in each `app/__init__.py` puts the repo
root on `sys.path` so `import shared` works regardless of cwd. Only 3 imports changed:
CLI + pipeline-test pipeline path, and the schemas `__init__` split.

## Communication
`Voice_backend` → HTTP (`httpx`) → `Voice_ML` (internal REST). The backend never
imports torch/whisper/NLLB/TTS/OpenVoice.

## Verification (all green)
| Check | Result |
|-------|--------|
| `Voice_ML` test suite | **38 passed** |
| `Voice_backend` test suite | **8 passed** |
| `Voice_ML` app imports + routes | ✅ `/ml/v1/health`, `/ml/v1/translate` |
| `Voice_backend` app imports + routes | ✅ `/api/v1/translate`, `/api/v1/jobs/{id}`, `/api/v1/health` |
| **Backend process loads NO ML libs** | ✅ verified (`torch/transformers/faster_whisper/whisper/TTS` absent from `sys.modules`) |

## Success criteria status (architecture)
- ✅ Voice_backend contains no ML inference (runtime-verified)
- ✅ Voice_ML contains all AI code
- ⏳ OpenVoice integrated — pending (see `PHASE2_ENVIRONMENT.md`)
- ⏳ Similarity > 70%, EN→NE / NE→EN with preservation, real execution — pending Phase 2 feature build
