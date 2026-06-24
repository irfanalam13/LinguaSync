# DEPLOYMENT REPORT (Phase 5.5 — live validation)

> Honest validation of the deployed stack. **Outcome: deployment is NOT operational** —
> none of the three services responded. Findings, root-cause analysis, and the code/config
> fixes applied are below. Values are real probe results, not fabricated.

## ⚠️ Security incident (action required)
A **live Neon Postgres connection string with its password** was shared in plaintext.
Treat it as **compromised**: rotate the Neon password immediately and set `VC_DATABASE_URL`
only as a dashboard env var. It is **not** stored in this repo or any report.

## Live probe results (external network)
| Service | URL | Result |
|---------|-----|--------|
| Backend | `linguasync-qjns.onrender.com` | **HTTP 000** on `/`, `/docs`, `/api/v1/health`, `/openapi.json` (no response within 15–100 s; one transient 404 early) |
| Voice_ML | `linguasync-1.onrender.com/ml/v1/health` | **HTTP 000** (timeout ~106 s) |
| Frontend | `lingua-sync-self.vercel.app` | **HTTP 404** at root |

→ The 10-point validation workflow (register → login → upload → job → queue → worker →
ML → storage → download → WebSocket) **could not be executed** because no service is reachable.

## Root-cause analysis
1. **Voice_ML — infeasible on a small/free Render instance (critical).** The ML stack
   (torch + transformers + OpenVoice + Wav2Lip + ffmpeg + multi-GB model downloads) needs
   **multiple GB of RAM/disk and ideally a GPU**. Free/512 MB tiers OOM or time out → the
   service never comes up. Requires a Docker image (with ffmpeg + the venv stack) on a
   **large/GPU plan**.
2. **Backend — not serving.** All paths hang (HTTP 000). Most likely: a suspended free
   instance whose cold start isn't completing, a failed start command, or a crash loop.
   Contributing code-level risks (now fixed): Postgres driver and a health check that
   depended on the (down) ML service.
3. **Frontend — Vercel 404.** The Next.js app lives in `web/`; Vercel's **Root Directory**
   is almost certainly not set to `web/` (or build output misconfigured).

## Fixes applied in this repo (code/config — committable, no new features)
- **DB driver**: `app/db/base.py` auto-normalizes `postgresql://` / `postgres://` →
  `postgresql+psycopg://` (psycopg v3), supporting Neon's `sslmode`/`channel_binding`.
  Added `psycopg[binary]`, `sqlalchemy`, `alembic`, `redis`, `rq`, `minio`, `email-validator`
  to `Voice_backend/requirements.txt`.
- **Health decoupling**: `/api/v1/health` is now a **fast liveness** probe (no downstream
  calls); ML reachability moved to `/api/v1/ready`. Prevents health-check cascades.
- **`render.yaml`** blueprint (backend web + worker + ML docker) with `healthCheckPath`,
  build = `pip install … && alembic upgrade head`, secrets as `sync:false`.
- **`web/vercel.json`** (Next framework). Backend tests still green (26).

## Dashboard actions required (cannot be done from code)
1. **Rotate the Neon password** (above) and set `VC_DATABASE_URL` on Render.
2. **Vercel**: set Root Directory = `web/`; set `NEXT_PUBLIC_API_URL` / `BACKEND_URL`. Redeploy.
3. **Render backend**: confirm start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
   set env (DB/Redis/JWT/MinIO/ML URL/CORS), run `alembic upgrade head`, and **check the
   service logs** for the actual start error.
4. **Render Voice_ML**: move to a Docker image + large/GPU plan; pre-bake or persist models.
5. Provision **Redis** and **MinIO** (or managed S3) and wire their env vars; run the worker.

## Re-validation
Once the services respond, the 10-point workflow can be run end-to-end (the backend flow is
already proven locally with the eager/local stack — see backend tests). Re-run probes against
`/api/v1/health`, `/ml/v1/health`, and the frontend root; then execute register→…→download.
