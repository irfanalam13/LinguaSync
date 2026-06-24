# PHASE 2 ENVIRONMENT

## Isolation principle

The **validated Phase 1 runtime must not be modified.** Phase 1 ML runs in the
**global** user site-packages (`C:\Users\admin\AppData\Roaming\Python\Python313`,
Python 3.13): torch 2.12, transformers 5.12, faster-whisper, SpeechT5, NLLB. Those
versions are frozen.

All Phase 2 inference — Resemblyzer **and** OpenVoice — runs in a **separate**
environment so nothing can downgrade/break the Phase 1 stack:

```
Voice_ML/.venv     ← uv-managed virtualenv, Python 3.12.13   (Phase 2 runtime)
```

## Why a new venv (not the global env)

- Resemblyzer pulls `librosa`/`numba`/`webrtcvad`, and OpenVoice pins **old**
  `numpy`/`librosa` — installing either globally risks the protected Phase 1 stack.
- No Python 3.10/3.11 is available here (OpenVoice's happy path). Python **3.12** (via
  `uv`) is the closest viable interpreter and is isolated from the 3.13 global env.
- HuggingFace model weights live in the shared user cache (`~/.cache/huggingface`), so
  they are **not** re-downloaded into the venv — only pip packages are reinstalled.

## Creating the environment

```bash
cd Voice_ML
uv venv --python 3.12 .venv
uv pip install --python ./.venv/Scripts/python.exe -r requirements.txt
```

`requirements.txt` installs the modern ML stack (torch, transformers, faster-whisper,
sentencepiece, sacremoses, accelerate, scipy) **plus** `resemblyzer` for similarity.

## ffmpeg

Static build (no system install / admin needed):
`C:\Users\admin\tools\ffmpeg\ffmpeg-8.1.1-essentials_build\bin`. Point the ML service at
it via `VC_FFMPEG_PATH` / `VC_FFPROBE_PATH`.

## OpenVoice (not on PyPI) — EXACT working install

OpenVoice is **git-clone only**. Installing its `requirements.txt` would pin
numpy 1.22 / librosa 0.9.1 / whisper-timestamped / gradio and **break the modern stack**,
so it is installed `--no-deps` with only the minimal runtime deps the ToneColorConverter
actually needs (whisper/pydub/gradio are avoided by skipping `se_extractor`):

```bash
cd Voice_ML
git clone --depth 1 https://github.com/myshell-ai/OpenVoice
uv pip install --python ./.venv/Scripts/python.exe --no-deps -e ./OpenVoice
# text-frontend deps (small, pure-python) imported by openvoice.api at load time:
uv pip install --python ./.venv/Scripts/python.exe inflect eng_to_ipa pypinyin jieba cn2an
# watermark model deps (api.py imports wavmark unconditionally):
uv pip install --python ./.venv/Scripts/python.exe --no-deps wavmark
uv pip install --python ./.venv/Scripts/python.exe resampy
# V2 converter checkpoint:
mkdir -p checkpoints_v2/converter
curl -L -o checkpoints_v2/converter/config.json   https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter/config.json
curl -L -o checkpoints_v2/converter/checkpoint.pth https://huggingface.co/myshell-ai/OpenVoiceV2/resolve/main/converter/checkpoint.pth
```

`VC_OPENVOICE_CKPT` defaults to `Voice_ML/checkpoints_v2/converter`.

### Integration gotchas (resolved, recorded for reproducibility)
- **`enable_watermark=False` is broken** — `ToneColorConverter.__init__` forwards the
  kwarg to its parent which rejects it. We install `wavmark` and let the watermark load.
- **Watermark message must be non-empty** — an empty `message` crashes `string_to_bits`;
  we use `VC_OPENVOICE_MESSAGE="VCPHASE2"`.
- **`se_extractor` (whisper/pydub) is bypassed** — we call `extract_se([wav])` directly,
  so no whisper-timestamped / faster-whisper-0.9 / pydub install is needed.

> **Outcome:** the `--no-deps` + selective-install strategy worked — OpenVoice runs in the
> Python 3.12 venv alongside modern torch 2.12 / numpy 2.4 with **no conflict** and **no
> change to the protected Phase 1 stack**. The `docker/openvoice/` and second-venv
> fallbacks were not needed.

## Fallback: Docker

`docker/openvoice/` can hold a dedicated image if local install proves unworkable; the
ML service would call it over HTTP exactly like any other backend.

## Status
- ✅ `Voice_ML/.venv` created (Python 3.12.13).
- ✅ ML stack + resemblyzer installed (torch 2.12.1+cpu, transformers 5.12.1).
- ✅ OpenVoice cloned + V2 converter checkpoint + integrated (`--no-deps`).
- ✅ Real EN→NE / NE→EN with preservation executed (see `REAL_PHASE2_REPORT.md`).
- ✅ **Protected Phase 1 global env unchanged** (verified post-run).
