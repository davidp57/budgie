"""Tests for the encryption management service.

Covers setup_user_encryption and verify_user_passphrase, including
verification that stored Argon2 params are used on unlock.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from budgie.services.encryption import setup_user_encryption, verify_user_passphrase


def _make_user(**overrides: object) -> MagicMock:
    """Create a mock User instance with sensible encryption defaults."""
    user = MagicMock()
    user.encryption_salt = None
    user.challenge_blob = None
    user.argon2_params = None
    user.is_encrypted = False
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


@pytest.mark.asyncio
async def test_setup_user_encryption_sets_fields() -> None:
    """setup_user_encryption must populate all encryption fields on the user."""
    db = AsyncMock()
    user = _make_user()

    key = await setup_user_encryption(db, user, "my-passphrase")

    assert len(key) == 32
    assert user.encryption_salt is not None
    assert user.challenge_blob is not None
    assert user.argon2_params is not None
    assert user.is_encrypted is True
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_user_encryption_stores_argon2_params_as_json() -> None:
    """The stored argon2_params must be valid JSON with expected keys."""
    db = AsyncMock()
    user = _make_user()

    await setup_user_encryption(db, user, "my-passphrase")

    params = json.loads(user.argon2_params)
    assert "time_cost" in params
    assert "memory_cost" in params
    assert "parallelism" in params


@pytest.mark.asyncio
async def test_verify_user_passphrase_correct_returns_key() -> None:
    """Correct passphrase must return the derived key."""
    db = AsyncMock()
    user = _make_user()
    passphrase = "correct-horse-battery-staple"

    await setup_user_encryption(db, user, passphrase)
    result = await verify_user_passphrase(user, passphrase)

    assert result is not None
    assert len(result) == 32


@pytest.mark.asyncio
async def test_verify_user_passphrase_wrong_returns_none() -> None:
    """Wrong passphrase must return None."""
    db = AsyncMock()
    user = _make_user()
    passphrase = "correct-horse-battery-staple"

    await setup_user_encryption(db, user, passphrase)
    result = await verify_user_passphrase(user, "wrong-passphrase")

    assert result is None


@pytest.mark.asyncio
async def test_verify_uses_stored_argon2_params() -> None:
    """verify_user_passphrase must use the stored argon2_params, not the defaults.

    Stores the key derived with default params, then patches argon2_params to
    use non-default values.  Verification must fail because the re-derived key
    will differ from the challenge blob that was created with the original params.
    """
    db = AsyncMock()
    user = _make_user()
    passphrase = "correct-horse-battery-staple"

    await setup_user_encryption(db, user, passphrase)

    # Overwrite stored params with deliberately different values
    user.argon2_params = json.dumps(
        {"time_cost": 1, "memory_cost": 65536, "parallelism": 4}
    )

    # Re-derive with wrong params → challenge blob verification must fail
    result = await verify_user_passphrase(user, passphrase)
    assert result is None


@pytest.mark.asyncio
async def test_verify_user_passphrase_not_set_up_returns_none() -> None:
    """User with no encryption setup must return None."""
    user = _make_user()
    result = await verify_user_passphrase(user, "any-passphrase")
    assert result is None
