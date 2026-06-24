# RESULTS (Phase 5 — Step 15)

Completed-job results are surfaced in the `JobCard` (and can be promoted to a dedicated
`/jobs/[id]` route).

## Features
- **Video preview** — inline `<video controls>` streaming `GET /api/v1/jobs/{id}/result`.
- **Download** — download button hitting the same authenticated result endpoint
  (`localized_{id}.mp4`).
- **Similarity score** — speaker-similarity % (Resemblyzer-primary; from the clone/localize job).
- **Processing metrics** — mode, target language, status, progress; per-stage timings are
  available from Voice_ML and can be persisted to the job for a richer metrics panel.

## Dedicated results route (extension)
`web/src/app/jobs/[id]/page.tsx` can fetch a single job (`api.getJob`) and render a fuller
results view (transcript, translated text, timings table, similarity breakdown). The data is
already exposed by the job API; this is a presentation add.
