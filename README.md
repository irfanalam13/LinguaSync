# pip install -r requirements.txtVoice Converter — Phase 1 MVP (English ⇄ Nepali Video Translation)

Translate the spoken audio of a video between **English** and **Nepali**, fully
offline with free/local models. No voice cloning, no speaker preservation, no lip
sync — just a clean translation pipeline.

```
video.mp4 → extract audio → speech-to-text → translate → text-to-speech → merge → output.mp4
```

| Stage                    | Technology                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| Audio extract / mux      | **ffmpeg** (safe argv, no shell)                                                        |
| Speech-to-text           | **faster-whisper** (fallback: openai-whisper) — auto language detect + timestamps      |
| Translation              | **NLLB-200** (`facebook/nllb-200-distilled-600M`)                                     |
| Text-to-speech (English) | **MMS-TTS** (`facebook/mms-tts-eng`, VITS)                                            |
| Text-to-speech (Nepali)  | **SpeechT5** (`aryamanstha/speecht5_tts_nepali_...`) + `microsoft/speecht5_hifigan` |

> The TTS layer is **engine-agnostic and per-language**. MMS-TTS has no Nepali voice
> (`facebook/mms-tts-npi` does not exist — discovered during the real run, see `BLOCKERS.md`),
> so Nepali uses a transformers-native SpeechT5 finetune. Both engines are free + offline.
> Nepali audio fidelity is limited by free-model quality — see `BLOCKERS.md` #2.

---

## Architecture

```
                 ┌──────────────┐        ┌───────────────────────┐
   CLI  ─────────▶              │        │  services/            │
                 │  pipeline    │───────▶│   video_service       │ ffmpeg
   HTTP ─────────▶  (orchestr.) │        │   transcription_serv. │ faster-whisper
   /api/v1/      │              │        │   translation_service │ NLLB-200
   translate     └──────┬───────┘        │   tts_service         │ MMS-TTS
                        │                └───────────────────────┘
                        ▼
              artifacts/<job_id>/  →  audio.wav, transcript.txt,
                                       translated.txt, translated.wav, output.mp4
```

All heavy models are **lazy singletons** — imported/downloaded only on first use, so
the app starts instantly and the test suite runs with no ML stack installed.

### Folder structure

```
voice_converter/
├── PHASE1_ANALYSIS.md          # pre-implementation repo audit
├── TEST_REPORT.md              # test results, benchmarks, known limitations
├── docker-compose.yml
└── Voice_backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── pytest.ini
    └── app/
        ├── main.py             # FastAPI app factory
        ├── api/routes.py       # POST /api/v1/translate, GET /api/v1/health
        ├── cli/main.py         # python -m app.cli.main
        ├── core/               # config, logging, device, exceptions
        ├── schemas/            # pydantic contracts
        ├── services/           # video / transcription / translation / tts / pipeline
        ├── utils/              # job ids, artifact dirs
        └── tests/              # 44 mocked tests (no GPU / no ffmpeg needed)
```

---

## Installation

**1. System dependency — ffmpeg** (required; not a pip package):

| OS            | Command                                                      |
| ------------- | ------------------------------------------------------------ |
| Windows       | `winget install Gyan.FFmpeg` (or `choco install ffmpeg`) |
| macOS         | `brew install ffmpeg`                                      |
| Debian/Ubuntu | `sudo apt-get install -y ffmpeg`                           |

Verify: `ffmpeg -version`. If it isn't on PATH, set `VC_FFMPEG_PATH=/full/path/to/ffmpeg`.

**2. Python deps** (Python 3.10–3.12 recommended for the ML wheels):

```bash
cd Voice_backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

For a CUDA GPU, install the matching torch build from https://pytorch.org first.
Models (~2–3 GB total) download automatically on first run to the HuggingFace cache.

---

## CLI usage

```bash
cd Voice_backend

# English video → Nepali audio
python -m app.cli.main input.mp4 --target ne

# Nepali video → English audio (auto-detects source)
python -m app.cli.main input.mp4 --target en

# Force the source language, set a job id, silence progress
python -m app.cli.main input.mp4 --target en --source ne --job-id demo1 --quiet
```

Output prints the job id, direction, output path, and per-stage timings. All
artifacts land in `artifacts/<job_id>/`.

---

## API usage

```bash
cd Voice_backend
uvicorn app.main:app --reload          # http://127.0.0.1:8000  (Swagger at /docs)
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/translate \
  -F "file=@input.mp4" \
  -F "target=ne"
```

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "completed",
  "output_video": ".../artifacts/a1b2c3d4e5f6/output.mp4",
  "source_language": "en",
  "target_language": "ne",
  "timings": { "audio_extraction": 1.2, "transcription": 9.4, "translation": 3.1,
               "tts": 5.0, "video_render": 0.8, "total": 19.5 }
}
```

Health probe: `GET /api/v1/health` → device, ffmpeg availability, supported languages.

### Docker

```bash
docker compose up --build      # ffmpeg baked into the image
```

---

## Configuration

All settings are overridable via `VC_*` env vars or a `.env` file in `Voice_backend/`:

| Var                      | Default                              | Meaning                       |
| ------------------------ | ------------------------------------ | ----------------------------- |
| `VC_DEVICE`            | `auto`                             | `auto` / `cpu` / `cuda` |
| `VC_FFMPEG_PATH`       | `ffmpeg`                           | ffmpeg binary path            |
| `VC_ASR_MODEL`         | `base`                             | whisper model size            |
| `VC_TRANSLATION_MODEL` | `facebook/nllb-200-distilled-600M` | NLLB checkpoint               |
| `VC_ARTIFACTS_DIR`     | `./artifacts`                      | per-job output root           |

---

## Testing

```bash
cd Voice_backend
python -m pytest          # 44 tests, fully mocked — no models/ffmpeg required
```

See `TEST_REPORT.md` for results, benchmarks, and known limitations.
