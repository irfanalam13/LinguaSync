# PHASE 1 — Repository Analysis

> Audit performed before any code was written. Snapshot of the repository as it
> existed at commit `571ddd9` ("Initial commit").

## Existing Architecture

The repository contained a thin, partially-broken FastAPI + Celery skeleton:

```
Voice_backend/
  app/
    main.py                  # FastAPI() + include_router
    api/routes.py            # POST /upload -> kicks off celery task
    core/config.py           # EMPTY (0 bytes)
    services/
      asr.py                 # whisper.load_model("base") at import time
      translate.py           # placeholder stub, returns a fake string
      tts.py                 # Coqui TTS English-only, loaded at import time
      video.py               # ffmpeg via shell=True string interpolation
      pipeline.py            # synchronous orchestration, hardcoded en->ne
    workers/
      celery_app.py          # BROKEN: references undefined names at import
      tasks.py               # BROKEN: stray @router.get, no router imported
  requirements.txt           # no version pins; missing torch/faster-whisper
  Dockerfile
docker-compose.yml           # references ./backend (path does not exist)
README.md                    # EMPTY
```

The intended flow was: upload video → Celery worker → extract audio → Whisper
ASR → translate → Coqui TTS → ffmpeg merge → return path.

## Reusable Components

| Component | Verdict | Notes |
|-----------|---------|-------|
| FastAPI app bootstrap (`main.py`) | **Reuse (refactor)** | Keep the pattern, move to an app factory + versioned router. |
| Pipeline stage ordering (`pipeline.py`) | **Reuse (concept)** | The extract→ASR→translate→TTS→merge sequence is correct; implementation rewritten. |
| ffmpeg idea (`video.py`) | **Reuse (concept)** | ffmpeg is the right tool; the shell-string implementation is replaced with safe argv lists. |
| Whisper ASR (`asr.py`) | **Refactor** | Right model family; replaced with faster-whisper + lazy loading + language detection + segments. |

## Bad Design Decisions

1. **Eager model loading at import** (`asr.py`, `tts.py`): `whisper.load_model()` and
   `TTS(...)` run on `import`. Any import (including test collection) downloads/loads
   multi-GB models and crashes if torch is absent. Models must be lazy singletons.
2. **`shell=True` with f-string interpolation** (`video.py`): command injection risk and
   breaks on paths with spaces (common on Windows). Must use argv lists.
3. **Hardcoded relative output paths** (`audio.wav`, `output.wav`, `final.mp4`): concurrent
   jobs collide; no per-job isolation.
4. **Hardcoded translation direction** (`pipeline.py` always `en->ne`): ignores the
   `--target` requirement and Nepali→English direction.
5. **No configuration layer**: `core/config.py` is empty; paths, device, model names hardcoded.
6. **No error handling**: ffmpeg return codes ignored (`subprocess.run` without `check`).

## Technical Debt

- `requirements.txt` has **zero version pins** and omits `torch`, `faster-whisper`,
  `transformers`, `sentencepiece` — the install is not reproducible and won't actually run.
- `translate.py` is a **placeholder** returning `"[Translated en->ne]: ..."` — not a translator.
- `tts.py` is **English-only** (`ljspeech/tacotron2`) — cannot produce Nepali, which is the
  whole point of the Nepali direction.
- No tests, no logging, no schemas, no CLI.

## Missing Features

- `core/config.py` content, structured logging, custom exceptions, device auto-detection.
- `schemas/` (pydantic models), `cli/`, `utils/`, `tests/`.
- Real translation (NLLB-200), language auto-detection, timestamped transcription.
- Nepali-capable TTS.
- Per-job artifact directory, stage timing, `POST /api/v1/translate`.

## Unused / Dead Code

- **`app/workers/celery_app.py`** — references `extract_audio.s`, `video_path`, `merge_video`
  at module scope; these are undefined, so the module **raises on import**. Dead.
- **`app/workers/tasks.py`** — defines `@router.get("/status/...")` but never imports a
  `router`; `NameError` on import. Dead.
- **Celery / Redis / Flower** entirely — not in the Phase 1 requirement list, and the MVP
  spec wants a synchronous `status: "completed"` response. **Deleted** in favor of synchronous
  in-process processing (simpler, fewer moving parts). Can return in a later phase for scale.

## Refactoring Plan

1. **Delete** `app/workers/` (broken Celery), and the old `asr.py / translate.py / tts.py /
   video.py / pipeline.py` (rewritten under the required service names).
2. **Create** the mandated tree: `api/ services/ schemas/ core/ cli/ tests/ utils/`.
3. **`core/`**: `config.py` (pydantic-settings: paths, device, model names, ffmpeg path),
   `logging.py` (structured per-stage timing), `exceptions.py`, `device.py` (CPU/GPU auto).
4. **`services/`**: `video_service.py` (safe argv ffmpeg + validation/metadata),
   `transcription_service.py` (faster-whisper → whisper fallback, lazy singleton, language
   auto-detect, segments), `translation_service.py` (NLLB-200, en<->ne, lazy),
   `tts_service.py` (offline, **Nepali + English** capable, lazy), `pipeline.py`
   (orchestration, artifacts, timing, both directions).
5. **`cli/main.py`** and **`api/routes.py`** as thin adapters over `pipeline`.
6. **Tests** mock all heavy models + ffmpeg so the suite is green without GPUs/downloads.
7. **Fix** `requirements.txt` (pinned), `Dockerfile`, `docker-compose.yml`.

## Key Engineering Decision — TTS backend

The spec lists XTTS-v2 / Coqui TTS as the preferred TTS. **Neither supports Nepali**, which
would make Acceptance Test 1 (English video → Nepali audio) impossible. The chosen default is
**Meta MMS-TTS** (`facebook/mms-tts-eng`, `facebook/mms-tts-npi`) via `transformers`:
fully offline, free, supports **both** English and Nepali, and reuses the `transformers` stack
already pulled in for NLLB. The TTS layer is engine-agnostic (`synthesize(text, language)`),
so Coqui/XTTS or `pyttsx3` can be swapped in for English without touching callers. Rationale is
recorded here and in "Known Limitations".

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Python 3.13 lacks wheels for some ML deps (e.g. Coqui `TTS`) | High | Default TTS = MMS-TTS (transformers, 3.13-OK). Coqui optional. |
| ffmpeg not installed on host | High | `video_service.validate` + `core.config` ffmpeg-path check; clear error. Tests mock ffmpeg. |
| Multi-GB model downloads on first run | Medium | Lazy singletons; document pre-download; tests never load real models. |
| CPU-only inference is slow | Medium | Auto GPU detection; `base`/`distilled` model defaults; documented perf targets. |
| Nepali TTS quality | Medium | MMS-TTS is intelligible but not studio-grade; noted in limitations. |
