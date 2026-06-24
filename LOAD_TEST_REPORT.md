# LOAD TEST REPORT (Phase 5.5)

> **Honest status: load testing was NOT performed — the target services are unreachable.**
> No synthetic results are fabricated. The only measurable signal was connection behaviour.

## Why not run
Load testing requires a responding system. Live probes returned **HTTP 000 (timeout)** for
the backend and Voice_ML, and **404** for the frontend (see DEPLOYMENT_REPORT.md). Running
1/5/10/20-user scenarios against a down service would only re-measure timeouts, and driving
20 real ML jobs would also be irresponsible (each localize job is minutes of CPU/GPU and
multi-GB) on an unprovisioned host.

## What was measured (reachability, not load)
| Target | Observation |
|--------|-------------|
| Backend `/api/v1/health` | no response within 15–100 s (HTTP 000), repeated |
| Voice_ML `/ml/v1/health` | no response (~106 s, HTTP 000) |
| Frontend `/` | HTTP 404 |

## Methodology to use once services are up (ready to run)
Tooling: `hey`/`k6`/`locust` for HTTP; the WebSocket and job pipeline measured separately.

1. **API latency** (light endpoints: `/health`, `/auth/login`, `/jobs` list) at concurrency
   **1, 5, 10, 20**; record p50/p95/p99 and error rate.
2. **Queue latency**: time from `POST /jobs` (enqueue) to worker pickup (status `running`),
   via Redis/RQ metrics — keep ML mocked or use the shortest `translate` mode to isolate
   queueing from inference.
3. **Processing time**: per-mode wall-clock from the worker timings already captured in
   Phase 1–4 reports (ASR/translate/TTS/clone/lip-sync) — do **not** stress with 20 concurrent
   real ML jobs on a single ML node; scale workers/ML replicas instead.
4. **CPU / memory**: Render dashboard metrics (or `docker stats` locally) during each tier.

## Expected bottleneck (from Phase 1–4 benchmarks)
Inference dominates: a `localize` job is ~3.5 min on CPU (lip-sync ~2 min). Concurrency is
bounded by **ML capacity**, not the API. Scale via multiple RQ workers + multiple Voice_ML
replicas/GPU; the API/queue layer handles far higher concurrency than the ML tier.

## Conclusion
Load testing is **blocked** on deployment. Bring the services up (DEPLOYMENT_REPORT.md fixes),
then run the methodology above and replace this section with real p50/p95/p99 + resource graphs.
