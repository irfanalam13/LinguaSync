# WEBSOCKET ARCHITECTURE (Phase 5 — Step 9)

## Endpoint
`WS /api/v1/ws/jobs/{job_id}?token=<access_jwt>`

Browsers can't set WS headers, so the access token is passed as a query param; it is
validated (type=`access`, owner check) **before** the socket is accepted (else closed with
1008 policy-violation).

## Protocol
After accept, the server emits JSON progress frames:
```json
{"job_id":"…","status":"running","progress":45,"stage":"inference","similarity":null,"error":null}
```
until a terminal status (`completed`/`failed`/`cancelled`), then closes. Frames are polled
from the DB (~1 s cadence). Disconnects are handled cleanly.

## Live progress
With the **rq** backend, the worker updates `Job.progress`/`stage` as it runs, so the WS
streams real-time updates + queue position. With the **eager** backend the job finishes
during the create request, so the WS immediately reports `completed` (expected in dev).

## Scaling note
DB polling is fine for modest concurrency. For many concurrent watchers, switch to **Redis
pub/sub**: the worker publishes progress to `job:{id}` and the WS subscribes — removes
per-connection polling. Documented as the next step; not required for Phase 5 acceptance.

## Files
`app/api/ws.py`.
