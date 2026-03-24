"""Cryptography service: AES-256-GCM encryption and Argon2id key derivation.

All user data fields are encrypted at rest using AES-256-GCM with a unique
random nonce per encryption. The encryption key is derived from the user's
passphrase via Argon2id and never stored on disk.

Encrypted fields are stored as base64(nonce || ciphertext || tag) strings.
"""

import base64
import os

from argon2.low_level import Type, hash_secret_raw
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── Constants ─────────────────────────────────────────────────────────────────

_KEY_LENGTH = 32  # 256 bits
_NONCE_LENGTH = 12  # 96-bit nonce recommended for AES-GCM
_CHALLENGE_PLAINTEXT_LENGTH = 32  # random bytes encrypted in the challenge blob

# Argon2id parameters — OWASP recommended minimums for interactive use
_ARGON2_TIME_COST = 3
_ARGON2_MEMORY_COST = 65536  # 64 MiB
_ARGON2_PARALLELISM = 4
_ARGON2_HASH_LEN = _KEY_LENGTH


# ── Exceptions ────────────────────────────────────────────────────────────────


class InvalidKeyError(Exception):
    """Raised when decryption fails due to a wrong key or tampered ciphertext."""


# ── Key derivation ────────────────────────────────────────────────────────────


def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Derive a 256-bit encryption key from a passphrase using Argon2id.

    Args:
        passphrase: The user's secret passphrase (plaintext).
        salt: A 16-byte random salt stored alongside the user record.

    Returns:
        32-byte derived key suitable for AES-256-GCM.
    """
    return hash_secret_raw(
        secret=passphrase.encode(),
        salt=salt,
        time_cost=_ARGON2_TIME_COST,
        memory_cost=_ARGON2_MEMORY_COST,
        parallelism=_ARGON2_PARALLELISM,
        hash_len=_ARGON2_HASH_LEN,
        type=Type.ID,
    )


def generate_salt() -> bytes:
    """Generate a cryptographically random 16-byte Argon2 salt.

    Returns:
        16 random bytes.
    """
    return os.urandom(16)


# ── Field encryption / decryption ─────────────────────────────────────────────


def encrypt_field(plaintext: str, key: bytes) -> str:
    """Encrypt a single data field with AES-256-GCM.

    A unique random nonce is generated per call — the same plaintext encrypted
    twice will produce different ciphertexts.

    The returned string is base64(nonce || ciphertext || tag).

    Args:
        plaintext: The string value to encrypt.
        key: A 32-byte AES-256 key.

    Returns:
        Base64-encoded string: nonce (12 bytes) + ciphertext + GCM tag (16 bytes).
    """
    nonce = os.urandom(_NONCE_LENGTH)
    aesgcm = AESGCM(key)
    # AESGCM.encrypt appends the 16-byte GCM tag to the ciphertext
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)
    blob = nonce + ciphertext_with_tag
    return base64.b64encode(blob).decode()


def decrypt_field(ciphertext: str, key: bytes) -> str:
    """Decrypt a single data field encrypted with encrypt_field.

    Args:
        ciphertext: Base64-encoded string produced by encrypt_field.
        key: The 32-byte AES-256 key used during encryption.

    Returns:
        The original plaintext string.

    Raises:
        InvalidKeyError: If the key is wrong or the ciphertext has been tampered
            with (GCM authentication tag mismatch).
    """
    try:
        blob = base64.b64decode(ciphertext)
        nonce = blob[:_NONCE_LENGTH]
        ciphertext_with_tag = blob[_NONCE_LENGTH:]
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext_bytes.decode()
    except (InvalidTag, Exception) as exc:
        raise InvalidKeyError(
            "Decryption failed: wrong key or tampered ciphertext."
        ) from exc


# ── Challenge blob ────────────────────────────────────────────────────────────


def create_challenge_blob(key: bytes) -> str:
    """Create a challenge blob for key verification.

    Encrypts a random 32-byte payload with the given key. The blob can later be
    used to verify that a candidate key is correct, by attempting decryption and
    checking that the GCM authentication tag validates.

    Args:
        key: The 32-byte encryption key to embed in the challenge.

    Returns:
        Base64-encoded challenge blob (same format as encrypt_field output).
    """
    random_payload = os.urandom(_CHALLENGE_PLAINTEXT_LENGTH)
    return encrypt_field(random_payload.hex(), key)


def verify_challenge_blob(blob: str, key: bytes) -> bool:
    """Verify a candidate key against a previously created challenge blob.

    Args:
        blob: Challenge blob created by create_challenge_blob.
        key: The candidate key to verify.

    Returns:
        True if the key is correct (GCM tag validates), False otherwise.
    """
    try:
        decrypt_field(blob, key)
        return True
    except InvalidKeyError:
        return False
