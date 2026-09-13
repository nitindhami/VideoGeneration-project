"""Application configuration and settings."""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent


class Settings(BaseSettings):
    APP_NAME: str = "CineShorts AI"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True

    # ── LLM Settings ──────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    DEFAULT_LLM_MODEL: str = "gemini-2.5-pro"       # Upgraded from flash
    FALLBACK_LLM_MODEL: str = "gemini-2.5-flash"

    # ── Research Settings ─────────────────────────────────────────
    DEEP_RESEARCH_ENABLED: bool = False              # Toggle (costs ~$1-3/task)
    DEEP_RESEARCH_MODEL: str = "deep-research-preview-04-2026"

    # ── Text-to-Speech ────────────────────────────────────────────
    # Priority: gemini-tts -> elevenlabs -> edge-tts -> macos-say
    TTS_PROVIDER: str = "auto"       # auto | gemini-tts | elevenlabs | edge-tts
    ELEVENLABS_API_KEY: str = ""
    GEMINI_TTS_MODEL: str = "gemini-2.5-pro-preview-tts"
    DEFAULT_VOICE: str = "en-US-ChristopherNeural"
    TTS_SPEECH_RATE: str = "+10%"    # Viral pacing: slightly faster
    TTS_SPEECH_PITCH: str = "+0Hz"

    # ── Image Generation ──────────────────────────────────────────
    # Priority: gemini-3 -> imagen-ultra -> replicate -> pollinations -> procedural
    IMAGE_PROVIDER: str = "auto"     # auto | gemini-3 | imagen-ultra | replicate | pollinations
    IMAGE_QUALITY: str = "production" # economy | production | ultra
    REPLICATE_API_TOKEN: str = ""
    GEMINI_IMAGE_MODEL: str = "gemini-3-pro-image-preview"
    IMAGEN_MODEL: str = "imagen-4.0-ultra-generate-001"
    REPLICATE_IMAGE_MODEL: str = "black-forest-labs/flux-1.1-pro"
    IMAGES_PER_SCENE: int = 2        # 1=economy, 2-3=production multi-cut

    # ── Video Engine & AI Models ──────────────────────────────────
    VIDEO_ENGINE_MODE: str = "fast_motion"   # fast_motion | gemini_omni | minimax | luma | hybrid
    AI_VIDEO_MODEL: str = "gemini-omni-1.1-flash"
    AI_VIDEO_RESOLUTION: str = "720p"        # 720p | 1080p

    # ── Video Editing ─────────────────────────────────────────────
    EDIT_STYLE: str = "fast_cuts"    # fast_cuts | cinematic | hybrid
    MUSIC_ENABLED: bool = True
    MUSIC_VOLUME_DB: float = -18.0   # Background music level (dBFS)
    VOICE_VOLUME_DB: float = -6.0    # Narration level (dBFS)

    # ── Storage & Server ──────────────────────────────────────────
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    STORAGE_DIR: Path = WORKSPACE_ROOT / "storage"
    OUTPUT_DIR: Path = WORKSPACE_ROOT / "storage" / "outputs"
    TEMP_DIR: Path = WORKSPACE_ROOT / "storage" / "temp"

    # ── CORS ──────────────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    class Config:
        env_file = [WORKSPACE_ROOT / ".env", PROJECT_ROOT / ".env"]
        extra = "ignore"


settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
