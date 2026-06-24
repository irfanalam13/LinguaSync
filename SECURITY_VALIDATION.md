# SECURITY VALIDATION (Phase 5.5)

> Live black-box testing was **blocked** (services unreachable), so this validates the
> security posture from the **code** (verified by the backend test suite, 26 passing) and
> flags what still needs live verification. Honest status — nothing assumed-passing.

## Findings

### 1. JWT — ✅ verified in code/tests
- Access/refresh tokens, `type`-scoped (access/refresh/reset/verify); replay across purposes
  rejected. Refresh **rotation + revocation** (logout, password reset). Bad/expired/garbage
  tokens → 401. Covered by `test_auth.py`. *Live:* re-confirm against the running API.

### 2. Upload validation — ✅ verified in code/tests
- Extension allow-list (`.mp4/.mov/.mkv/.webm/.avi/.m4v`) → 422; size cap 500 MB (streamed)
  → 413; empty → 422. Storage keys path-traversal-guarded. `test_video_job_flow.py` covers
  type rejection. *Recommend:* add server-side `ffprobe` content validation before queueing.

### 3. CORS — ✅ configured, ⏳ live-unverified
- `CORSMiddleware` with an explicit origin allow-list (`VC_CORS_ORIGINS`; set to the Vercel
  origin in `render.yaml`). Could not verify response headers live (backend down).

### 4. File restrictions — ✅ (see Upload validation)
- Type + size + traversal guard enforced server-side and client-side.

### 5. Rate limiting — ❌ NOT implemented (gap)
- No rate limiting on `/auth/*` or uploads. **This is a real gap** flagged since Phase 5
  (SECURITY_REPORT.md). Recommend `slowapi` (or a Redis token bucket) on login/register/
  password-reset and upload before public exposure. Brute-force/abuse currently unthrottled.

## Additional observations
- **Secret exposure (critical):** a live DB credential was shared in plaintext — rotate now.
- `VC_JWT_SECRET` defaults to a dev value; **must** be overridden in prod (env, not committed).
- Ownership scoping verified: cross-user video/job access → 404 (no existence leak).
- Password-reset request does not reveal account existence (always 200).
- HTTPS/HSTS/secure-cookie posture depends on the platform (Render/Vercel terminate TLS);
  tokens are currently in `localStorage` (XSS exposure) — consider `HttpOnly` cookies.

## Verdict
**Core auth/upload/ownership controls are sound (code-verified).** Blocking gaps before a
real public launch: (a) **rotate the leaked credential**, (b) **add rate limiting**,
(c) set production `JWT_SECRET`, (d) live-verify CORS/HTTPS once deployed. Optional hardening:
ffprobe content scan, virus-scan hook, cookie-based tokens.
