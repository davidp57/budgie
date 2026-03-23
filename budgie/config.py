"""Application configuration loaded from environment variables.

Uses pydantic-settings to load and validate configuration from .env file
and environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'budgie.db'}"

    # Auth / JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # MVP: skip authentication, hardcode user_id=1
    mvp_mode: bool = False

    # File uploads
    upload_dir: str = str(DATA_DIR / "uploads")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:5173,https://localhost:5173,http://localhost:8080"


settings = Settings()
