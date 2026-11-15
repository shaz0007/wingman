import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Settings:
    """Application configuration loaded from environment variables."""

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS Configuration: comma-separated list of origins
    _cors_raw: str = os.getenv(
        "CORS_ORIGINS",
        os.getenv(
            "web_origin",
            "http://localhost:4000,http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173,https://wingman-woi7.vercel.app"
        )
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        if not self._cors_raw:
            return ["*"]
        origins = [origin.strip() for origin in self._cors_raw.split(",") if origin.strip()]
        return origins if origins else ["*"]

    # AI API Keys & Models
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "").strip()
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()

    # Speech to Text Configuration
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "").strip()
    GNANI_API_URL: str = os.getenv("GNANI_API_URL", "https://api.vachana.ai/stt/v3").strip()

    # Constraints & Rate Limits
    MAX_AUDIO_SIZE_BYTES: int = int(os.getenv("MAX_AUDIO_SIZE_BYTES", str(15 * 1024 * 1024)))  # 15 MB
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Provider Availability Helpers
    @property
    def is_gemini_configured(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def is_groq_configured(self) -> bool:
        return bool(self.GROQ_API_KEY)

    @property
    def is_gnani_configured(self) -> bool:
        return bool(self.GNANI_API_KEY)


settings = Settings()
