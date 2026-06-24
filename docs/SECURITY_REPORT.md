# SECURITY REPORT (Phase 5)

> What's implemented now vs. recommended hardening before public launch. Honest status.

## Implemented
| Control | Status | Where |
|---------|--------|-------|
| Password hashing | ✅ bcrypt (per-salt) | `core/security.py` |
| JWT auth | ✅ access/refresh, purpose-typed (`type` claim) | `core/security.py`, `api/deps.py` |
| Refresh rotation + revocation | ✅ jti tracked; revoked on logout & password reset | `services/auth_service.py` |
| Ownership scoping | ✅ all video/job reads/writes filtered by `user_id` (404, no leak) | `api/videos.py`, `api/jobs.py` |
| File-type validation | ✅ extension allow-list (client + server) | `api/videos.py` |
| Upload size cap | ✅ streamed, 500 MB → 413 | `api/videos.py` |
| Path-traversal guard (storage) | ✅ key resolution check | `services/storage.py` |
| CORS | ✅ configurable allow-list | `main.py`, `config.cors_origins` |
| Account-existence non-disclosure | ✅ password-reset request always 200 | `api/auth.py` |
| Secrets via env | ✅ `VC_JWT_SECRET` etc. (dev default flagged) | `core/config.py` |

## Recommended before launch (not yet implemented — documented honestly)
- **Rate limiting** — add `slowapi`/Redis token-bucket on `/auth/*` (login, register, reset)
  and uploads. *(Hook point: FastAPI middleware.)*
- **Virus / content scan hook** — scan uploads (e.g. ClamAV) before processing; the upload
  handler is the integration point (quarantine on the storage layer).
- **Content validation** — verify uploads are real media via `ffprobe` before queueing
  (Voice_ML already validates; do it at upload for fast rejection).
- **HTTPS / HSTS, secure cookies** — terminate TLS at the platform (Render/Vercel); if moving
  tokens to cookies, set `HttpOnly`/`Secure`/`SameSite`.
- **Production secrets** — replace `jwt_secret` default; rotate; use a secret manager.
- **Email verification enforcement** — currently informational; gate sensitive actions on
  `is_verified` if desired.
- **Dependency / image scanning**, request body limits at the proxy, audit logging.

## Notes
No payment/PII-heavy data is stored (per scope). The AI stack runs in the isolated Voice_ML
service; the backend never executes untrusted media itself beyond ffprobe/ffmpeg.
