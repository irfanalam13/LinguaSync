# STORAGE ARCHITECTURE (Phase 5 — Step 4)

> Verified via the local backend (flow tests store + retrieve real files).

## Design
A single `Storage` interface (`put_file / get_file / delete / exists`) with two backends,
selected by `VC_STORAGE_BACKEND`:
- **`local`** (dev/tests) — files under `VC_STORAGE_DIR`; path-traversal-guarded keys.
- **`minio`** (prod) — S3-compatible object store via the `minio` client (lazy import);
  auto-creates the bucket.

Callers (upload API, worker, downloads) are storage-agnostic.

## Object key layout
```
videos/{user_id}/{video_id}{ext}     # uploaded source videos
results/{job_id}/final_output.mp4    # localized output produced by the worker
```

## MinIO via Docker (prod-like)
```bash
docker run -d --name voice-minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
pip install minio   # backend env only
export VC_STORAGE_BACKEND=minio VC_MINIO_ENDPOINT=localhost:9000 VC_MINIO_BUCKET=voice-platform
```

## Files
`app/services/storage.py` (`Storage`, `LocalStorage`, `MinioStorage`, `get_storage`).
Config: `storage_backend`, `storage_dir`, `minio_*`.

## Limitations
Presigned download URLs (MinIO) not yet implemented — downloads currently stream through
the API (`GET /jobs/{id}/result`). Presigned URLs are a straightforward add for scale.
