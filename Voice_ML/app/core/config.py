"""Central configuration.

All tunables (model names, directories, device, ffmpeg path) live here and are
overridable via environment variables (prefix ``VC_``) or a ``.env`` file, so the
same code runs unchanged on a laptop (CPU) and a GPU box.
"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.device import resolve_device

# Repository root = .../Voice_backend
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings, populated from env (``VC_*``) / ``.env`` with defaults."""

    model_config = SettingsConfigDict(
        env_prefix="VC_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Directories -------------------------------------------------------
    base_dir: Path = BASE_DIR
    artifacts_dir: Path = BASE_DIR / "artifacts"
    uploads_dir: Path = BASE_DIR / "uploads"
    logs_dir: Path = BASE_DIR / "logs"
    models_dir: Path = BASE_DIR / "models"
    speaker_dir: Path = BASE_DIR / "temp" / "speaker"  # Phase 2 speaker embeddings
    speakers_dir: Path = BASE_DIR / "storage" / "speakers"  # Phase 3 persisted profiles

    # ---- Compute -----------------------------------------------------------
    device: str = Field(default="auto", description="auto | cpu | cuda")

    # ---- ffmpeg ------------------------------------------------------------
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"

    # ---- ASR (faster-whisper preferred, openai-whisper fallback) -----------
    asr_model: str = "base"
    asr_beam_size: int = 5

    # ---- Translation (NLLB-200) -------------------------------------------
    translation_model: str = "facebook/nllb-200-distilled-600M"
    translation_max_length: int = 512

    # ---- TTS (offline; per-language engine — see tts_service) --------------
    # English: MMS-TTS (VITS). Nepali: SpeechT5 finetune + HiFi-GAN vocoder,
    # because MMS-TTS has NO Nepali checkpoint (see BLOCKERS.md). The TTS layer
    # is engine-agnostic and selects the backend per language.
    tts_model_en: str = "facebook/mms-tts-eng"
    tts_model_ne: str = "aryamanstha/speecht5_tts_nepali_oslr43_tokenizermodified"
    tts_vocoder: str = "microsoft/speecht5_hifigan"
    tts_speaker_seed: int = 42  # fixed generic SpeechT5 speaker (no preservation in Phase 1)

    # ---- Audio -------------------------------------------------------------
    sample_rate: int = 16000

    # ---- API ---------------------------------------------------------------
    max_upload_mb: int = 500

    # ---- Phase 2: speaker preservation (OpenVoice ToneColorConverter) ------
    # Checkpoint dir holds config.json + checkpoint.pth (OpenVoice V2 converter).
    openvoice_ckpt: str = str(BASE_DIR / "checkpoints_v2" / "converter")
    openvoice_message: str = "VCPHASE2"  # non-empty watermark message (required by OpenVoice)

    # ---- Phase 3: voice cloning -------------------------------------------
    clone_sample_seconds: float = 30.0   # max speaker-sample length used
    clone_segment_seconds: float = 6.0   # multi-reference segment length

    # ---- Phase 4: lip sync (Wav2Lip) --------------------------------------
    wav2lip_dir: str = str(BASE_DIR / "Wav2Lip")
    wav2lip_checkpoint: str = str(BASE_DIR / "Wav2Lip" / "checkpoints" / "wav2lip_gan.pth")
    lipsync_max_width: int = 270   # downscale face video for tractable CPU inference
    lipsync_fps: int = 20
    lipsync_max_seconds: float = 0.0  # 0 = full length; >0 trims for speed

    @property
    def resolved_device(self) -> str:
        """Concrete device (``cpu``/``cuda``) after honouring availability."""
        return resolve_device(self.device)

    def ensure_dirs(self) -> None:
        """Create all runtime directories (idempotent)."""
        for d in (self.artifacts_dir, self.uploads_dir, self.logs_dir, self.models_dir, self.speaker_dir):
            Path(d).mkdir(parents=True, exist_ok=True)

    def ffmpeg_available(self) -> bool:
        """True if the configured ffmpeg binary is resolvable on PATH."""
        return shutil.which(self.ffmpeg_path) is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings instance."""
    return Settings()
