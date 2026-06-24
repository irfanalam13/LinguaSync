# BLOCKERS — Phase 1 Real Execution

## BLOCKER #1 — Nepali TTS model does not exist (RESOLVED via engine swap)

### Status

Discovered during the real EN→NE run. **Fix applied and re-validated** (see
`REAL_ACCEPTANCE_REPORT.md`). Earlier pipeline stages were unaffected.

### What worked in the real run

- ✅ Audio extraction (ffmpeg) → `audio.wav`
- ✅ Transcription (faster-whisper `base`, auto-detect → `en`) → `transcript.txt`
  - `"The weather today is bright and sunny many people are walking in the par near the river."`
- ✅ Translation (NLLB-200 distilled-600M, en→ne) → `translated.txt`
  - `"आज मौसम उज्यालो र घामको छ धेरै मानिसहरु नदी नजिकैको पार्कमा हिंडिरहेका छन्।"` (valid Nepali Devanagari)

### Exact error (stack trace, abridged)

```
File "app/services/pipeline.py", line 112, in run_pipeline
    tts_service.synthesize(translation.translated_text, target_language, translated_wav, settings)
File "app/services/tts_service.py", line 71, in synthesize
    _load(language, settings)
File "app/services/tts_service.py", line 53, in _load
    raise ModelLoadError(f"Failed to load TTS model for '{language}': {e}") from e
app.core.exceptions.ModelLoadError: Failed to load TTS model for 'ne':
  facebook/mms-tts-npi is not a local folder and is not a valid model identifier
  listed on 'https://huggingface.co/models'
```

### Root cause

Phase 1 configured the Nepali TTS voice as `facebook/mms-tts-npi`. **That checkpoint
does not exist.** Verified against the HuggingFace Hub:

| Model id                 | HTTP / result                                          | Note                               |
| ------------------------ | ------------------------------------------------------ | ---------------------------------- |
| `facebook/mms-tts-eng` | 200 ✅                                                 | English exists (used successfully) |
| `facebook/mms-tts-npi` | 401 / "not a valid model identifier"                   | **does not exist**           |
| `facebook/mms-tts-nep` | 401                                                    | does not exist                     |
| `facebook/mms-tts-npl` | 200 — but it is**Nahuatl (Puebla)**, NOT Nepali | wrong language                     |

MMS-TTS simply **has no Nepali voice**. The Phase 1 `PHASE1_ANALYSIS.md` assumption
("MMS-TTS supports both English and Nepali") was incorrect for Nepali. English was
fine; the Nepali leg could never have worked.

### Recommended fix (applied)

Use the already-engine-agnostic TTS layer to route **Nepali** to a different,
**transformers-native** engine that requires **no forbidden Phase-2 installs**
(SpeechT5 is built into `transformers`; no OpenVoice/XTTS/CosyVoice/Fish Speech):

- **English (`en`)** → `facebook/mms-tts-eng` (VITS) — unchanged, verified working.
- **Nepali (`ne`)** → SpeechT5 (`SpeechT5ForTextToSpeech`) finetuned on Nepali
  (`aryamanstha/speecht5_tts_nepali_oslr43_tokenizermodified`) +
  `microsoft/speecht5_hifigan` vocoder.

The `tts_service` interface (`synthesize(text, language, out_path)`) is unchanged; only
the per-language backend selection changed — exactly the extension point the Phase 1
design reserved for this.

### Prevention

- Added a config-time note that TTS model ids must be Hub-verified per language.
- The acceptance run now asserts a **non-empty, playable** `translated.wav` so a
  missing/broken voice fails loudly instead of silently.

---

## BLOCKER #2 — Nepali audio fidelity (ASR + free TTS quality) — RESOLVED on real input

### Status

**Resolved for acceptance.** NE→EN now **PASSES end-to-end on a real human Nepali clip**
with faster-whisper `small` (auto-detected `ne`, coherent translation, all artifacts) —
see `REAL_ACCEPTANCE_REPORT_NE_EN.md`. The original symptoms were caused by (a) a
*synthetic* Nepali test input that no ASR could read, and (b) whisper-`base`'s weak Nepali
ASR. Both addressed: use real audio + `small`/larger. A *residual quality* caveat remains
(ASR accuracy on casual Nepali is moderate; `medium`/`large`/GPU improve it) — quality, not
a blocker.

### Symptom

- `translated.wav` for the **Nepali** leg (EN→NE) is intelligible-but-robotic (generic speaker).
- The **NE→EN** round trip produced garbage text: transcript `"Ta ta ta ta"` →
  translation `"I'm going to tell you something."`

### Root cause

Two compounding free-model limitations:

1. **Free offline Nepali TTS is low quality.** The SpeechT5-Nepali community model with a
   generic speaker embedding produces audio that whisper cannot transcribe — verified:
   whisper `base` **and** `small` (forced `ne`) return empty/garbage on it.
2. **whisper-`base` Nepali ASR is weak**, and language auto-detect on degraded Nepali
   audio misfires to `en` (prob 0.60).

Because the NE→EN test *input* was itself synthetic Nepali TTS, this is **garbage-in →
garbage-out**, not a pipeline defect. The EN→NE text path (English ASR + NLLB) is accurate.

### Recommended fix

| Option                                                                                     | Effort | Effect                                             |
| ------------------------------------------------------------------------------------------ | ------ | -------------------------------------------------- |
| Use a**real human Nepali** clip for NE→EN testing                                   | low    | Removes the synthetic-input problem                |
| Default Nepali/auto runs to**whisper `small`/`medium`** (`VC_ASR_MODEL=small`) | low    | Much stronger Nepali ASR                           |
| Replace SpeechT5-Nepali with a higher-fidelity Nepali TTS (e.g. Indic Parler-TTS)          | medium | Better Nepali audio (extra dep)                    |
| Run on**GPU**                                                                        | env    | Lets larger ASR models be used at acceptable speed |

These are quality improvements, deferred so they can be weighed against Phase 2 (which
changes the TTS/voice stack anyway for speaker preservation).
