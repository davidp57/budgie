"""Tests for the cryptography service.

Covers AES-256-GCM encrypt/decrypt, Argon2id key derivation,
challenge blob creation and verification, and nullable-field helpers.

TDD — tests written before implementation.
"""

import base64

import pytest
from budgie.services.crypto import (
    InvalidKeyError,
    create_challenge_blob,
    decrypt_field,
    decrypt_str,
    derive_key,
    encrypt_field,
    encrypt_str,
    verify_challenge_blob,
)

# ── Constants ─────────────────────────────────────────────────────────────────

PASSPHRASE = "my secret passphrase for testing"
SALT = b"\x01" * 16  # deterministic salt for tests


# ── Key derivation ─────────────────────────────────────────────────────────────


def test_derive_key_returns_32_bytes() -> None:
    """Derived key must be exactly 32 bytes (256 bits)."""
    key = derive_key(PASSPHRASE, SALT)
    assert len(key) == 32


def test_derive_key_is_deterministic() -> None:
    """Same passphrase + salt always produces the same key."""
    key1 = derive_key(PASSPHRASE, SALT)
    key2 = derive_key(PASSPHRASE, SALT)
    assert key1 == key2


def test_derive_key_differs_with_different_passphrase() -> None:
    """Different passphrases must produce different keys."""
    key1 = derive_key(PASSPHRASE, SALT)
    key2 = derive_key("another passphrase", SALT)
    assert key1 != key2


def test_derive_key_differs_with_different_salt() -> None:
    """Different salts must produce different keys."""
    key1 = derive_key(PASSPHRASE, b"\x01" * 16)
    key2 = derive_key(PASSPHRASE, b"\x02" * 16)
    assert key1 != key2


# ── Encrypt / Decrypt ─────────────────────────────────────────────────────────


def test_encrypt_field_returns_base64_string() -> None:
    """encrypt_field must return a base64-decodable string."""
    key = derive_key(PASSPHRASE, SALT)
    ciphertext = encrypt_field("hello", key)
    assert isinstance(ciphertext, str)
    # Must be valid base64
    decoded = base64.b64decode(ciphertext)
    assert len(decoded) > 0


def test_encrypt_field_non_deterministic() -> None:
    """Same plaintext encrypted twice must produce different ciphertexts."""
    # Different nonces must produce different outputs even for identical plaintext.
    key = derive_key(PASSPHRASE, SALT)
    ct1 = encrypt_field("hello", key)
    ct2 = encrypt_field("hello", key)
    assert ct1 != ct2


def test_decrypt_field_round_trip() -> None:
    """decrypt_field must recover the original plaintext."""
    key = derive_key(PASSPHRASE, SALT)
    plaintext = "Compte courant BNP"
    ciphertext = encrypt_field(plaintext, key)
    recovered = decrypt_field(ciphertext, key)
    assert recovered == plaintext


def test_decrypt_field_with_wrong_key_raises() -> None:
    """Decrypting with the wrong key must raise InvalidKeyError (GCM tag mismatch)."""
    key = derive_key(PASSPHRASE, SALT)
    wrong_key = derive_key("wrong passphrase", SALT)
    ciphertext = encrypt_field("sensitive data", key)
    with pytest.raises(InvalidKeyError):
        decrypt_field(ciphertext, wrong_key)


def test_decrypt_field_with_tampered_ciphertext_raises() -> None:
    """Tampered ciphertext must raise InvalidKeyError."""
    key = derive_key(PASSPHRASE, SALT)
    ciphertext = encrypt_field("sensitive data", key)
    # Flip a byte in the middle of the base64-decoded blob
    raw = bytearray(base64.b64decode(ciphertext))
    raw[20] ^= 0xFF
    tampered = base64.b64encode(bytes(raw)).decode()
    with pytest.raises(InvalidKeyError):
        decrypt_field(tampered, key)


def test_encrypt_decrypt_various_types() -> None:
    """encrypt/decrypt must work for integers and special characters."""
    # Amounts are passed as strings; empty strings and unicode must round-trip.
    key = derive_key(PASSPHRASE, SALT)
    for value in ["", "0", "1050", "Épicerie Leclerc", "€100.00"]:
        assert decrypt_field(encrypt_field(value, key), key) == value


# ── Challenge blob ─────────────────────────────────────────────────────────────


def test_create_challenge_blob_returns_string() -> None:
    """Challenge blob must be a non-empty string."""
    key = derive_key(PASSPHRASE, SALT)
    blob = create_challenge_blob(key)
    assert isinstance(blob, str)
    assert len(blob) > 0


def test_verify_challenge_blob_with_correct_key() -> None:
    """Correct key must pass challenge verification."""
    key = derive_key(PASSPHRASE, SALT)
    blob = create_challenge_blob(key)
    assert verify_challenge_blob(blob, key) is True


def test_verify_challenge_blob_with_wrong_key() -> None:
    """Wrong key must fail challenge verification without raising (returns False)."""
    key = derive_key(PASSPHRASE, SALT)
    wrong_key = derive_key("wrong passphrase", SALT)
    blob = create_challenge_blob(key)
    assert verify_challenge_blob(blob, wrong_key) is False


def test_challenge_blob_is_non_deterministic() -> None:
    """Each call must produce a different blob (random plaintext inside)."""
    key = derive_key(PASSPHRASE, SALT)
    blob1 = create_challenge_blob(key)
    blob2 = create_challenge_blob(key)
    assert blob1 != blob2


# ── derive_key with custom params ─────────────────────────────────────────────


def test_derive_key_with_custom_params_matches_explicit_call() -> None:
    """Passing explicit Argon2id params must produce the same key as the defaults."""
    key_default = derive_key(PASSPHRASE, SALT)
    key_explicit = derive_key(
        PASSPHRASE, SALT, time_cost=3, memory_cost=65536, parallelism=4
    )
    assert key_default == key_explicit


def test_derive_key_with_different_params_differs() -> None:
    """Different Argon2id params must produce a different derived key."""
    key_default = derive_key(PASSPHRASE, SALT)
    key_lower = derive_key(
        PASSPHRASE, SALT, time_cost=1, memory_cost=65536, parallelism=4
    )
    assert key_default != key_lower


# ── decrypt_field invalid input ────────────────────────────────────────────────


def test_decrypt_field_with_invalid_base64_raises() -> None:
    """Passing a non-base64 string must raise InvalidKeyError (ValueError path)."""
    key = derive_key(PASSPHRASE, SALT)
    with pytest.raises(InvalidKeyError):
        decrypt_field("not-valid-base64!!!", key)


# ── encrypt_str / decrypt_str nullable helpers ────────────────────────────────


def test_encrypt_str_with_none_value_returns_none() -> None:
    """encrypt_str must return None when value is None."""
    key = derive_key(PASSPHRASE, SALT)
    assert encrypt_str(None, key) is None


def test_encrypt_str_with_none_key_returns_plaintext() -> None:
    """encrypt_str must return the plaintext unchanged when key is None."""
    assert encrypt_str("hello", None) == "hello"


def test_encrypt_str_round_trip() -> None:
    """encrypt_str + decrypt_str must recover the original plaintext."""
    key = derive_key(PASSPHRASE, SALT)
    plaintext = "Boulangerie Dupont"
    ciphertext = encrypt_str(plaintext, key)
    assert ciphertext is not None
    assert ciphertext != plaintext  # must be encrypted
    recovered = decrypt_str(ciphertext, key)
    assert recovered == plaintext


def test_decrypt_str_with_none_value_returns_none() -> None:
    """decrypt_str must return None when value is None."""
    key = derive_key(PASSPHRASE, SALT)
    assert decrypt_str(None, key) is None


def test_decrypt_str_with_none_key_returns_raw() -> None:
    """decrypt_str must return the raw value unchanged when key is None."""
    assert decrypt_str("some-blob", None) == "some-blob"


def test_decrypt_str_with_wrong_key_returns_raw_value() -> None:
    """decrypt_str must return the raw stored value when decryption fails.

    This handles non-migrated plaintext rows read with an active session key.
    """
    key = derive_key(PASSPHRASE, SALT)
    wrong_key = derive_key("wrong passphrase", SALT)
    ciphertext = encrypt_str("sensitive memo", key)
    # Decrypting with wrong key returns the raw (ciphertext) value, not an exception.
    result = decrypt_str(ciphertext, wrong_key)
    assert result == ciphertext  # graceful fallback


def test_decrypt_str_with_plaintext_value_and_active_key_returns_raw() -> None:
    """decrypt_str on a plaintext (non-migrated) row must return that value unchanged.

    A plaintext memo is not valid base64 AES-GCM; decryption will fail and
    decrypt_str must fall back to returning the value as-is.
    """
    key = derive_key(PASSPHRASE, SALT)
    plaintext = "Courses Carrefour"  # not encrypted
    result = decrypt_str(plaintext, key)
    # Falls back to returning the raw value
    assert result == plaintext
