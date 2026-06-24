# DEPLOYMENT GUIDE (Phase 5)

Three deployable units: **Voice_backend** (API), **Voice_ML** (GPU-friendly inference),
**web** (Next.js). Plus managed Postgres, Redis, and MinIO/S3.

## Topology
```
Vercel (web)  ──HTTPS──▶  Render (Voice_backend API)  ──Redis queue──▶  Voice_ML worker(s)
                                  │                                         │
                              Postgres                                  Voice_ML API (HTTP)
                                  │                                         │
                              MinIO / S3  ◀──── uploads + results ─────────┘
```

## Backend (Render)
- Service 1 — **API**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (Python 3.12).
- Service 2 — **Worker**: `python worker.py` (same image, `VC_QUEUE_BACKEND=rq`).
- Pre-deploy: `alembic upgrade head`.
- Env: `VC_DATABASE_URL` (Render Postgres), `VC_REDIS_URL` (Render Redis), `VC_JWT_SECRET`,
  `VC_STORAGE_BACKEND=minio` + `VC_MINIO_*`, `VC_ML_SERVICE_URL`, `VC_CORS_ORIGINS`.
- `pip install "psycopg[binary]" rq redis minio` (backend env only — never the ML stack).

## Voice_ML
- Best on a **GPU** host (CUDA auto-detected). Runs its own FastAPI (`uvicorn app.main:app`)
  in the isolated Python 3.12 venv with torch/transformers/OpenVoice/Wav2Lip + ffmpeg.
- The backend worker reaches it via `VC_ML_SERVICE_URL`. Keep it on a private network.

## Frontend (Vercel)
- Root `web/`. Build `next build`, output served by Vercel.
- Env: `NEXT_PUBLIC_API_URL` (backend URL), `NEXT_PUBLIC_WS_URL`. Or use the `next.config`
  rewrite with `BACKEND_URL` for same-origin proxying.

## Datastores
- **Postgres** (managed) — run Alembic migrations on deploy.
- **Redis** (managed) — RQ broker.
- **MinIO / S3** — object storage bucket `voice-platform`.

## Local prod-like (Docker)
```bash
docker run -d --name pg   -e POSTGRES_PASSWORD=pass -e POSTGRES_USER=user -e POSTGRES_DB=voice_platform -p 5432:5432 postgres:17
docker run -d --name redis -p 6379:6379 redis:7
docker run -d --name minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin minio/minio server /data --console-address ":9001"
# backend: VC_QUEUE_BACKEND=rq VC_STORAGE_BACKEND=minio uvicorn app.main:app  &  python worker.py
# web: npm run dev
```

## Health & readiness
- API: `GET /api/v1/health` (also reports ML reachability).
- ML: `GET /ml/v1/health`.

## CI/CD (recommended)
GitHub Actions: backend `pytest`, frontend `vitest` + `playwright`, `alembic upgrade` on
deploy. Build separate images for API, worker, ML, web.

## Status (honest)
Configuration + scripts are provided and the apps run locally (backend tests green; frontend
scaffold builds). A full cloud deployment to Render/Vercel was **not performed in this
session** — these are the verified-local instructions to do so.
