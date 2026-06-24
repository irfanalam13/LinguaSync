# UPLOAD FLOW (Phase 5 — Step 13)

`web/src/features/upload/upload-dropzone.tsx`

## Features
- **Drag & drop** + click-to-browse (`onDrop`/hidden input).
- **Client-side validation** — extension allow-list (`.mp4 .mov .mkv .webm .avi .m4v`);
  mismatches show an inline error before any network call.
- **Upload** — `multipart/form-data` to `POST /api/v1/videos/upload`; returns the `Video` id,
  surfaced to the dashboard to create a job.
- **Progress / state animation** — animated upload spinner + filename; dropzone scales on
  drag-over (Framer Motion).
- **Errors** — server errors (size 413, type 422) surfaced inline.

## Thumbnail preview
A frame thumbnail can be generated client-side via a hidden `<video>` + `<canvas>` seek;
the dropzone is structured to drop this in (shows filename + file icon today).

## Backend pairing
Server enforces the same allow-list + a 500 MB cap (streamed in 1 MB chunks). See VIDEO_API.md.
