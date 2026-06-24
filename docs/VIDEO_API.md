# VIDEO API (Phase 5 — Step 7)

> Verified — upload/list/get/delete + validation covered by flow tests.

## Endpoints (`/api/v1/videos`, all Bearer-authenticated, owner-scoped)
| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/upload` | multipart `file` | 201 `VideoPublic` |
| GET | `` | — | list of the user's videos |
| GET | `/{id}` | — | `VideoPublic` (404 if not owner) |
| DELETE | `/{id}` | — | 204 (deletes storage object + row) |

## Upload handling
- Streamed to a temp file in 1 MB chunks; **size cap** `VC_MAX_UPLOAD_MB` (default 500) → 413.
- **File-type validation** by extension: `.mp4 .mov .mkv .webm .avi .m4v` → else 422.
- Empty upload → 422.
- Stored at `videos/{user_id}/{video_id}{ext}`; a `Video` row records filename, key,
  content_type, size.

## Ownership
Every read/delete is scoped to `Video.user_id == current_user.id`; other users get 404
(no existence leak).

## Files
`app/api/videos.py`, `app/schemas/video.py`, `app/db/models/video.py`.
