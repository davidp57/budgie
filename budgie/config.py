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

    # File uploads
    upload_dir: str = str(DATA_DIR / "uploads")
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    # SQL echo — separate from debug so production logs stay clean
    db_echo: bool = False

    # Rate limiting — set to False to disable (useful for testing)
    ratelimit_enabled: bool = True

    # CORS — comma-separated lists
    cors_origins: str = (
        "http://localhost:5173,https://localhost:5173,http://localhost:8080"
    )
    cors_allow_methods: str = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "Content-Type,Authorization"

    # Registration — set to False to prevent new sign-ups in production
    registration_enabled: bool = True

    # WebAuthn (Passkeys)
    webauthn_rp_id: str = "localhost"
    webauthn_rp_name: str = "Budgie"
    webauthn_origin: str = "https://localhost:5173"


settings = Settings()
