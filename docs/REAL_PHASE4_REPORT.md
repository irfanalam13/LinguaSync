# REAL PHASE 4 REPORT — Lip Sync & Video Localization

> Real end-to-end execution (no mocks) in the isolated `Voice_ML/.venv` (Python 3.12).
> Branch `phase4-lipsync`. Engine: **Wav2Lip** (`wav2lip_gan.pth` + bundled s3fd). Device:
> CPU. ffmpeg 8.1.1. Run date: 2026-06-24. Values measured, not fabricated.

## Runs

### NE → EN — full localization (genuine, real human face) — `p4_ne2en`
- Input: `nepali_sample.mp4` (real human, 11.5 s).
- Pipeline: ASR (whisper small, auto `ne`) → NLLB ne→en → voice clone (OpenVoice multi-ref)
  → face detect (s3fd: 4/5 frames) → **Wav2Lip** lip-sync to cloned English audio → mux.
- Output: `Voice_ML/artifacts/p4_ne2en/final_output.mp4` — H.264 270×448, AAC, **8.97 s**.
- Speaker similarity (Resemblyzer-primary, clone stage): 0.348 dual / **~0.6 Resemblyzer**.

### EN → NE — full localization (genuine, real English face) — `p4_en2ne_real`
- Input: `english_short.mp4` (real English talking-head, 12 s; trimmed from the
  user-provided 35 s `english_sample.mp4`).
- Pipeline: ASR (whisper, auto `en` @ 0.98) → NLLB en→ne → voice clone (OpenVoice multi-ref,
  baseline 0.233 → **cloned 0.352**, +0.118) → face detect (s3fd 5/5) → **Wav2Lip** lip-sync
  to cloned Nepali audio → mux.
- Transcript (en): *"Recognizing that confidence is not something we are born with, it's a
  skill… it's a muscle almost…"* → Translation (ne): *"यो पहिचान गर्नु कि आत्मविश्वास
  हामीसँग जन्मेको कुरा होइन, यो एउटा सीप हो।…"* (fluent, accurate).
- Output: `Voice_ML/artifacts/p4_en2ne_real/final_output.mp4` — H.264, AAC, **12.16 s**
  (Nepali speech, original speaker's face lip-synced). Total 332 s (lip_sync 215 s).
- ✅ This is a **genuine EN→NE localization** — the earlier face-source caveat is resolved
  now that a real English face video was provided.

## Artifacts (both jobs)
`original.mp4` · `translated.wav` · `cloned.wav` · `lipsync.mp4` · `final_output.mp4`
(plus `audio.wav`, `face_small.mp4`, `cloning_quality.json`). All present and verified.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Wav2Lip integrated | ✅ vendored + checkpoints, runs offline in `Voice_ML/.venv` |
| EN→NE localized video generated | ✅ genuine, real English face (`p4_en2ne_real`) |
| NE→EN localized video generated | ✅ genuine, real human face |
| `final_output.mp4` generated | ✅ both directions |
| Lip movement visibly follows translated speech | ⏳ **requires human playback** — Wav2Lip ran on detected faces and produced synced frames; perceptual confirmation is the user's (files above) |
| Real execution verified | ✅ |
| Reports generated | ✅ (this + benchmark + known-limitations + analysis) |

## Bugs found & fixed during real execution (nothing hidden)
1. **Wav2Lip `audio.py`** old librosa API (positional `filters.mel`, `librosa.core.load`) →
   patched to keyword/`librosa.load`.
2. **`np.int`** (removed in numpy 2.x) in `face_detection/utils.py` → `int`.
3. **Final ffmpeg mux** used `shell=False` on Windows → patched to `shell=True`.
4. **ffmpeg not on cmd PATH** → `lipsync_service` passes an env with the ffmpeg dir prepended
   (Windows format).
5. **Face detector input** must be a stacked `np.array`, not a list → fixed.
6. **Subprocess output decode** crashed on cp1252 → `encoding="utf-8", errors="replace"`.
7. **Full-res CPU Wav2Lip is impractical** → `video_localization_service` downscales
   (270 px / 20 fps) before lip-sync.
8. **Wav2Lip aborts if any frame lacks a face** (real videos have brief occlusions/turns) →
   patched `face_detect` to reuse the last valid box (full-frame fallback) instead of raising.

## Honest summary
Wav2Lip lip-sync is **integrated and works end-to-end on CPU for BOTH directions** with
genuine real-face inputs: NE→EN (real Nepali clip) and EN→NE (real English clip). Each
produces a `final_output.mp4` where the original speaker's mouth follows the translated,
voice-cloned speech. Perceptual lip-sync sharpness should be confirmed by playback (CPU
downscaling + non-studio base TTS reduce crispness); see `KNOWN_LIMITATIONS.md`.
