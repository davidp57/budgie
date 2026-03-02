"""Authentication service: password hashing and JWT management."""

import datetime

import bcrypt
from jose import JWTError, jwt

from budgie.config import settings


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt.

    Args:
        password: Plain text password.

    Returns:
        Bcrypt-hashed password string.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Stored bcrypt hash.

    Returns:
        True if passwords match, False otherwise.
    """
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict[str, object]) -> str:
    """Create a signed JWT access token.

    Args:
        data: Payload data to encode into the token.

    Returns:
        Signed JWT string.
    """
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # type: ignore[no-any-return]


def decode_token(token: str) -> dict[str, object]:
    """Decode and verify a JWT token.

    Args:
        token: JWT string to decode.

    Returns:
        Decoded payload dict.

    Raises:
        JWTError: If the token is invalid or expired.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])  # type: ignore[no-any-return]


__all__ = [
    "JWTError",
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
]
