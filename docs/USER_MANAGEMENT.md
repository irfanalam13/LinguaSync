# USER MANAGEMENT (Phase 5 — Step 3)

> Verified — covered by backend tests (26 total).

## Features
- **Profile**: `GET/PATCH /api/v1/users/me` (full_name, avatar_url).
- **Usage statistics**: `GET /api/v1/users/me/usage` → videos count + job counts by status.
- **API keys**: create / list / revoke.

## Endpoints
| Method | Path | Auth | Result |
|--------|------|------|--------|
| GET | `/api/v1/users/me` | Bearer | profile |
| PATCH | `/api/v1/users/me` | Bearer | updated profile |
| GET | `/api/v1/users/me/usage` | Bearer | `UsageStats` |
| POST | `/api/v1/users/me/api-keys` | Bearer | `ApiKeyCreated` (raw key shown **once**) |
| GET | `/api/v1/users/me/api-keys` | Bearer | list (prefix only, no secret) |
| DELETE | `/api/v1/users/me/api-keys/{id}` | Bearer | 204 (deactivate) |

## API keys
Format `vc_<token_urlsafe(32)>`. Only the **bcrypt hash** + a 10-char prefix are stored;
the raw key is returned once at creation. `user_service.authenticate_api_key` resolves a raw
key by prefix lookup + hash verify (for future API-key-authenticated requests). Revocation
sets `is_active=false`.

## Files
`app/schemas/user.py`, `app/services/user_service.py`, `app/api/users.py`,
`app/db/models/user.py` (`ApiKey`).
