# JOB API (Phase 5 — Step 8)

> Verified — create→queue→worker→complete→download covered by flow tests.

## Endpoints (`/api/v1/jobs`, Bearer, owner-scoped)
| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `` | `{video_id, target_language, source_language?, mode}` | 201 `JobPublic` (enqueued) |
| GET | `` | — | list of the user's jobs (newest first) |
| GET | `/{id}` | — | `JobPublic` (status/progress/similarity/result_key) |
| DELETE | `/{id}` | — | 204: queued/running → cancelled; terminal → deleted |
| GET | `/{id}/result` | — | `final_output.mp4` (200) or 409 if not ready |

## Modes
`translate` (P1) · `preserve` (P2) · `clone` (P3) · `localize` (P4, clone+lip-sync).
Validated: `video_id` must be owned; `source_language != target_language`; langs ∈ {en, ne}.

## Lifecycle
`queued → running → completed | failed | cancelled`. On create the job is enqueued; the
worker drives status/progress; the result is fetched from storage on download.

## Files
`app/api/jobs.py`, `app/schemas/job.py`, `app/db/models/job.py`.
