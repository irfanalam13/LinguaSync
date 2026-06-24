# BASELINE SIMILARITY REPORT (pre voice-conversion)

> The benchmark OpenVoice must improve on. Measured in the isolated `Voice_ML/.venv`
> (Python 3.12) with **Resemblyzer** speaker embeddings + cosine similarity, on the
> real Phase 1 artifacts. Run date: 2026-06-24.

## Method
For each direction, compare the **original speaker** (extracted source `audio.wav`)
against the **base TTS output** (`translated.wav`, no voice preservation) via cosine
similarity of 256-d Resemblyzer d-vectors. Resemblyzer captures voice *timbre*, so the
score is meaningful across languages (the synthesized voice is a different speaker than
the source → expected to be moderate/low).

## Results

| Case | Source audio | Base TTS engine | Baseline similarity |
|------|--------------|-----------------|--------------------:|
| EN → NE | English speaker (`real_en2ne/audio.wav`) | SpeechT5 Nepali | **0.5340** |
| NE → EN | Nepali speaker (`real_ne2en_human/audio.wav`) | MMS-TTS English | **0.4954** |
| **Average** | | | **0.5147** |

(Raw data: `Voice_ML/artifacts/baseline_similarity.json`.)

## Interpretation
The base TTS uses a **generic** voice unrelated to the source speaker, so similarity
sits around **~0.51**. The Phase 2 success criterion: **OpenVoice tone-color conversion
must raise similarity above this baseline** (target also >0.70 absolute per the spec).

## Pass condition for OpenVoice
- Must exceed the per-case baseline (EN→NE > 0.534, NE→EN > 0.495).
- Stretch/spec target: **> 0.70**.
- If OpenVoice does not improve over baseline → **Phase 2 voice-preservation FAILS**
  (reported honestly), independent of the architecture work which is already complete.
