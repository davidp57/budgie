"""Application configuration loaded from environment variables.

Uses pydantic-settings to load and validate configuration from .env file
and environment variables.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Signing keys published in this repository (the default below and the old
# value of ``.env.example``).  Anyone can forge a valid JWT with them.
_PUBLIC_SECRET_KEYS = frozenset(
    {"change-me-in-production", "change-me-to-a-random-string"}
)
SECRET_KEY_MIN_LENGTH = 32


def check_secret_key(secret_key: str) -> None:
    """Refuse a JWT signing key that is public or too short.

    Called at startup: a server signing tokens with a known key accepts
    tokens forged offline for any username, so it must not start at all.

    Args:
        secret_key: The configured ``SECRET_KEY``.

    Raises:
        RuntimeError: If the key is a published placeholder or shorter than
            :data:`SECRET_KEY_MIN_LENGTH` characters.
    """
    if secret_key in _PUBLIC_SECRET_KEYS or len(secret_key) < SECRET_KEY_MIN_LENGTH:
        raise RuntimeError(
            "SECRET_KEY is not configured: set it in .env to a random value of at "
            f"least {SECRET_KEY_MIN_LENGTH} characters, e.g. the output of "
            "`openssl rand -hex 32`. Changing it signs out every user."
        )


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = f"sqlite+aiosqlite:///{DATA_DIR / 'budgie.db'}"

    # Auth / JWT — the default is a placeholder that check_secret_key() rejects
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
