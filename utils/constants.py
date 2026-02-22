import os
from pathlib import Path
from dotenv import load_dotenv


class Constants:
    # =========================
    # Resolve Project Root
    # =========================
    BASE_DIR = Path(__file__).resolve().parent.parent
    ENV_PATH = BASE_DIR / ".env"

    # Load .env from root explicitly
    load_dotenv(dotenv_path=ENV_PATH)

    # =========================
    # Environment Variable Keys
    # =========================
    SUPABASE_URL_ENV: str = "SUPABASE_URL"
    SUPABASE_KEY_ENV: str = "SUPABASE_KEY"
    GEMINI_API_KEY_ENV: str = "GEMINI_API_KEY"
    ELEVENLABS_API_KEY_ENV: str = "ELEVENLABS_API_KEY"

    # =========================
    # Loaded Environment Values
    # =========================
    SUPABASE_URL: str | None = os.getenv(SUPABASE_URL_ENV)
    SUPABASE_KEY: str | None = os.getenv(SUPABASE_KEY_ENV)
    GEMINI_API_KEY: str | None = os.getenv(GEMINI_API_KEY_ENV)
    ELEVENLABS_API_KEY: str | None = os.getenv(ELEVENLABS_API_KEY_ENV)

    # =========================
    # Gemini Configuration
    # =========================
    GEMINI_DEFAULT_MODEL: str = "gemini-1.5-flash-latest"

    # =========================
    # ElevenLabs Configuration
    # =========================
    ELEVENLABS_DEFAULT_VOICE_ID: str = "default"