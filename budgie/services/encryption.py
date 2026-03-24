"""Encryption management service.

Handles user encryption setup and passphrase verification.
"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.user import User
from budgie.services.crypto import (
    create_challenge_blob,
    derive_key,
    generate_salt,
    verify_challenge_blob,
)

# Argon2id parameters used for key derivation (stored alongside salt).
_ARGON2_PARAMS: dict[str, int] = {
    "time_cost": 3,
    "memory_cost": 65536,
    "parallelism": 4,
}


async def setup_user_encryption(
    db: AsyncSession, user: User, passphrase: str
) -> bytes:
    """Set up encryption for a user for the first time.

    Derives an AES-256-GCM key from the passphrase using Argon2id,
    generates a random salt, creates a challenge blob for future
    passphrase verification, then stores all key material on the user row
    and sets ``is_encrypted = True``.

    Args:
        db: Async database session.
        user: The user to set up encryption for.
        passphrase: The chosen passphrase (plaintext).

    Returns:
        The derived AES-256-GCM key (32 bytes).
    """
    salt = generate_salt()
    key = derive_key(passphrase, salt)
    blob = create_challenge_blob(key)
    params_json = json.dumps(_ARGON2_PARAMS)

    user.encryption_salt = salt
    user.challenge_blob = blob
    user.argon2_params = params_json
    user.is_encrypted = True
    await db.commit()
    return key


async def verify_user_passphrase(user: User, passphrase: str) -> bytes | None:
    """Verify a passphrase against a user's stored challenge blob.

    Args:
        user: The user whose challenge blob to verify against.
        passphrase: The passphrase to check (plaintext).

    Returns:
        The derived AES-256-GCM key (32 bytes) if the passphrase is correct,
        ``None`` otherwise.
    """
    if user.encryption_salt is None or user.challenge_blob is None:
        return None
    key = derive_key(passphrase, user.encryption_salt)
    if not verify_challenge_blob(user.challenge_blob, key):
        return None
    return key
