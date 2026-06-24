# JOB MONITORING (Phase 5 — Step 14)

`web/src/features/jobs/job-card.tsx` + dashboard polling.

## Features
- **Live status** — per-job icon + label (queued/running/completed/failed/cancelled) and
  current `stage`.
- **Animated progress bar** — gradient fill driven by `job.progress` (0–100).
- **Similarity** — shows speaker-similarity % when available (cloning/localize jobs).
- **Result** — completed jobs render an inline `<video>` preview + download button.
- **Errors** — failed jobs show the error message.

## Live updates
Two mechanisms (both backed by the same DB job state):
1. **Polling** (implemented) — dashboard `useQuery` refetches every 1.5 s while any job is
   active; simple and robust.
2. **WebSocket** (backend ready) — `api.wsUrl(jobId, token)` →
   `/api/v1/ws/jobs/{id}?token=…` streams progress frames; drop-in for push updates +
   queue position (see WEBSOCKET_ARCHITECTURE.md).

## Retry
The job API supports re-running failed jobs (create a new job for the same video); a one-click
"Retry" button is a small addition to the card (hook: `api.createJob`).
