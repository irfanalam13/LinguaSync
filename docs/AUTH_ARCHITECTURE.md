# AUTH ARCHITECTURE (Phase 5 — Step 2)

> Branch `phase5-platform`. JWT auth with bcrypt + refresh-token rotation/revocation.
> **Status: built and verified** — 9 auth tests pass (21 backend total).

## Components
```
app/core/security.py          bcrypt hashing + JWT (access/refresh/reset/verify), typed by `type` claim
app/db/models/refresh_token.py  RefreshToken (jti, expires_at, revoked) for server-side revocation
app/services/auth_service.py   register / authenticate / issue / refresh / logout / reset / verify
app/api/deps.py                get_current_user (HTTPBearer → decode access token → load User)
app/api/auth.py                /api/v1/auth/* routes
app/schemas/auth.py            request/response models (EmailStr-validated)
```

## Tokens
- **Access** — short-lived (default 30 min), `{sub, type:"access"}`. Sent as `Authorization: Bearer`.
- **Refresh** — long-lived (default 14 days), `{sub, type:"refresh", jti}`. The `jti` is stored
  in `refresh_tokens`; **rotation** on each refresh (old jti revoked, new issued); revoked on logout
  and on password reset.
- **Reset / Verify** — purpose-scoped short-lived JWTs (`type:"reset"|"verify"`); a token issued for
  one purpose can't be replayed for another (enforced in `decode_token`).

bcrypt is used directly (clean with bcrypt 5.x); passwords truncated to bcrypt's 72-byte limit.

## Endpoints (`/api/v1/auth`)
| Method | Path | Body | Result |
|--------|------|------|--------|
| POST | `/register` | email, password, full_name | 201 + tokens (also mints a verify token) |
| POST | `/login` | email, password | 200 + tokens |
| POST | `/refresh` | refresh_token | 200 + rotated tokens |
| POST | `/logout` | refresh_token | 204 (revokes refresh) |
| POST | `/password-reset/request` | email | 200 (always; no existence leak) → reset token |
| POST | `/password-reset/confirm` | token, new_password | 204 (revokes all refresh tokens) |
| POST | `/verify-email` | token | 200 + user (is_verified=true) |
| GET | `/me` | — (Bearer) | 200 + current user |

## Security properties (tested)
- Duplicate email → **409**; wrong password / disabled / bad token → **401**.
- Refresh **rotation**: a used refresh token is rejected on reuse (replay protection).
- **Logout** and **password reset** revoke refresh tokens.
- Password-reset request **does not reveal** whether an email exists.
- `/me` rejects missing/garbage tokens.

## Email delivery
Reset/verify tokens are generated server-side; **delivery is a hook** (the reset token is
returned in the response for now). Wiring an SMTP/email provider is a later, non-inference
concern — not implemented to avoid an external dependency.

## Not yet (later steps)
Rate limiting on auth endpoints (Step: Security), API-key auth (Step 3), OAuth/social login
(out of scope per "no enterprise features").
