# WORKER ARCHITECTURE (Phase 5 — Step 6)

> Verified — `run_job` is exercised end-to-end by the flow tests (mocked Voice_ML).

## Responsibility
`app/jobs/worker.py :: run_job(job_id)` executes one job:
1. Load `Job`; set `running`, `started_at`, progress 5.
2. Pull the source video from object storage to a temp path (progress 10).
3. Build an `MLTranslateRequest` from the job's mode and call **Voice_ML over HTTP**
   (progress 20). Mode → flags: `translate`→{}, `preserve`→preserve_voice,
   `clone`→clone_voice, `localize`→localize.
4. Upload the produced `final_output.mp4` to storage as `results/{job_id}/final_output.mp4`
   (progress 90).
5. Set `completed`, progress 100, `result_key`, `similarity`, `finished_at`.
   On any error → `failed` + `error` (skips if already `cancelled`).

## Key property — NO ML in the worker
The worker never imports torch/whisper/OpenVoice/Wav2Lip. All inference stays in **Voice_ML**;
the worker only orchestrates storage ↔ HTTP ↔ DB. This preserves the protected AI stack and
keeps the backend image light.

## Execution modes
- **eager** — `run_job` called inline by the queue (dev/tests).
- **rq** — `python worker.py` runs an RQ `Worker` consuming the Redis queue; scale by running
  more worker processes.

## Progress
Persisted to `Job.progress`/`stage` and streamed via the WebSocket. (Fine-grained per-pipeline-
stage progress from Voice_ML would require Voice_ML→backend callbacks/pub-sub — a future add.)

## Files
`app/jobs/worker.py`, `worker.py` (entrypoint), `app/jobs/ml_client.py` (HTTP to Voice_ML).
