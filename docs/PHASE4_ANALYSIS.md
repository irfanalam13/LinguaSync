# PHASE 4 — Analysis (Lip Sync & Video Localization)

> Branch `phase4-lipsync` (from `phase3-voice-cloning`). Phases 1–3 authoritative and
> untouched. Adds visual lip synchronization on top of the Phase 3 clone pipeline.

## Objective
Produce fully localized video: translated + cloned speech **and** mouth movements that
match the new speech. Pipeline:

```
input video → extract face video + audio → ASR → translate → clone voice (OpenVoice)
            → Wav2Lip (lip sync to cloned audio) → final_output.mp4
```

## Reuse (no duplication)
- Entire Phase 3 path (`cloning_pipeline`: ASR→translate→base TTS→clone) — reused.
- `video_service` (ffmpeg), `core`, `shared`, backend/ML split, isolated `Voice_ML/.venv`.
- Phase 4 **adds** the lip-sync stage after cloned audio is produced.

## New modules
- `core/model_manager.py` — cached lazy model registry (CPU/GPU), avoids repeated loads.
- `services/face_detection_service.py` — detect speaking face / bounding boxes (Wav2Lip's
  bundled s3fd); single vs multiple faces.
- `services/lipsync_service.py` — drive Wav2Lip (face video + cloned audio → lip-synced video).
- `services/video_localization_service.py` — orchestrate face/audio extraction + final mux.
- `pipelines/localization_pipeline.py` — full Phase 4 pipeline.

## Engine
- **Primary: Wav2Lip** (Rudrabha). Not on PyPI → vendored from the complete HF mirror
  `camenduru/Wav2Lip` (code + `wav2lip_gan.pth` + bundled **s3fd** detector). Runs offline.
- **Fallback: SadTalker** — not installed unless Wav2Lip fails.

## Risk assessment (HIGH — this is the riskiest phase)
1. **Wav2Lip is a 2020 codebase** targeting Python 3.6; its `audio.py` uses the *old* librosa
   API (positional `librosa.filters.mel`, etc.) which breaks on librosa 0.10 in our venv.
   Mitigation: patch `audio.py` to keyword args; run inference as a subprocess with the venv
   python so it's isolated from our service imports.
2. **CPU-only Wav2Lip is slow** (per-frame face detection + GAN). Short clips only.
3. **Input must contain a detectable face.** Our `sample_en.mp4` is a synthetic test pattern
   with **no face** → Wav2Lip cannot lip-sync it. Only `nepali_sample.mp4` (real human) has a
   face. **Consequence:** NE→EN is fully demonstrable; **EN→NE needs an English talking-face
   video** that we do not have. This is an input-availability constraint, documented up front;
   a real English face clip would be requested (as `nepali_sample.mp4` was for Phase 1).
4. **Vertical/!= standard resolutions** and multi-face scenes: Wav2Lip handles one face well;
   multi-speaker/face-switching are explicit **stretch goals, out of scope** for acceptance.

## Face detection
- s3fd detects face boxes per frame. Single speaker → first/largest box. Multiple faces →
  Wav2Lip syncs the detected box(es); we document that robust multi-speaker tracking is a
  stretch goal not implemented here.

## Acceptance vs reality (honest, up front)
- Wav2Lip integration + NE→EN localized `final_output.mp4` with visible lip motion is the
  realistic real-execution target.
- EN→NE acceptance depends on obtaining an English face video; otherwise it is documented
  as input-limited (not a pipeline failure). Any Wav2Lip install/runtime blocker on Python
  3.12 will be reported in `KNOWN_LIMITATIONS.md` (not hidden).
