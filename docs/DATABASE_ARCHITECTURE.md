# DATABASE ARCHITECTURE (Phase 5 — Step 1)

> Branch `phase5-platform`. Backend foundation: SQLAlchemy 2.0 (sync) + Alembic.
> **Status: built and verified** — models + migrations create the schema; 4 DB tests
> pass; `alembic revision --autogenerate` + `upgrade head` succeed.

## Stack
- **SQLAlchemy 2.0** (typed `Mapped`/`mapped_column`, `DeclarativeBase`), **sync** engine
  (FastAPI deps and queue workers are sync).
- **Alembic** for migrations (`render_as_batch=True` for SQLite-safe ALTERs, `compare_type`).
- **SQLite** by default (dev/tests, zero-setup); **PostgreSQL 17** in prod via env.

## Configuration (env-driven, `VC_` prefix)
| Setting | Default | Prod example |
|---------|---------|--------------|
| `VC_DATABASE_URL` | `sqlite:///…/voice_platform.db` | `postgresql+psycopg://user:pass@host:5432/voice_platform` |
| `VC_DB_ECHO` | `false` | `false` |

## Files
```
Voice_backend/
├── alembic.ini
├── alembic/
│   ├── env.py                # uses Settings.database_url + Base.metadata
│   ├── script.py.mako
│   └── versions/656a18ea33b4_initial_schema.py   # initial (users, api_keys, videos, jobs)
└── app/db/
    ├── base.py               # engine, SessionLocal, Base
    ├── session.py            # get_db() dependency, create_all()
    └── models/
        ├── mixins.py         # UUIDMixin (32-char hex PK), TimestampMixin
        ├── user.py           # User, ApiKey
        ├── video.py          # Video
        └── job.py            # Job, JobMode, JobStatus (enums)
```

## Schema

### users
`id` (uuid hex PK) · `email` (unique, indexed) · `hashed_password` · `full_name` ·
`avatar_url` · `is_active` · `is_verified` · `created_at` · `updated_at`

### api_keys  (Step 3)
`id` · `user_id` → users (cascade) · `name` · `prefix` (indexed) · `hashed_key` · `is_active`

### videos  (Step 7)
`id` · `user_id` → users (cascade) · `filename` · `storage_key` (MinIO) · `content_type` ·
`size_bytes` · `duration_s` · `status` (uploaded/deleted)

### jobs  (Step 8)
`id` · `user_id` → users · `video_id` → videos · `target_language` · `source_language` ·
`mode` (translate/preserve/clone/localize — maps to Phases 1–4) ·
`status` (queued/running/completed/failed/cancelled, indexed) · `progress` (0–100) ·
`stage` · `result_key` (MinIO) · `similarity` · `error` · `queue_job_id` ·
`started_at` · `finished_at` · timestamps

### Relationships
`User 1—* Video`, `User 1—* Job`, `User 1—* ApiKey`, `Video 1—* Job`. User deletion
cascades to videos/jobs/api-keys (ORM cascade + DB `ondelete=CASCADE`).

## Migrations — usage
```bash
cd Voice_backend
export VC_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/voice_platform
python -m alembic upgrade head            # apply
python -m alembic revision --autogenerate -m "msg"   # new migration after model changes
```

## Postgres via Docker (prod-like local)
```bash
docker run -d --name voice-pg -e POSTGRES_PASSWORD=pass -e POSTGRES_USER=user \
  -e POSTGRES_DB=voice_platform -p 5432:5432 postgres:17
pip install "psycopg[binary]"   # backend env only; never the protected ML stack
```

## Verification (this step)
- `pytest app/tests/test_db_models.py` → **4 passed** (CRUD, unique email, cascade delete, enums).
- `alembic upgrade head` on a fresh DB → tables `users, api_keys, videos, jobs` created.
- Existing backend API tests still pass (**12 total**); no completed AI pipeline touched.
