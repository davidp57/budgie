"""Tests for User model encryption fields."""

import pytest
from budgie.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_user_has_is_encrypted_column(db_session: AsyncSession) -> None:
    """User.is_encrypted defaults to False for new users."""
    user = User(username="bob", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.is_encrypted is False


@pytest.mark.asyncio
async def test_user_has_encryption_salt_nullable(db_session: AsyncSession) -> None:
    """User.encryption_salt is None by default (not yet set up)."""
    user = User(username="bob", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.encryption_salt is None


@pytest.mark.asyncio
async def test_user_has_challenge_blob_nullable(db_session: AsyncSession) -> None:
    """User.challenge_blob is None by default (not yet set up)."""
    user = User(username="bob", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.challenge_blob is None


@pytest.mark.asyncio
async def test_user_has_argon2_params_nullable(db_session: AsyncSession) -> None:
    """User.argon2_params is None by default (not yet set up)."""
    user = User(username="bob", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.argon2_params is None


@pytest.mark.asyncio
async def test_user_encryption_fields_can_be_set(db_session: AsyncSession) -> None:
    """All encryption fields can be stored and retrieved correctly."""
    salt = b"\x00" * 16
    user = User(
        username="carol",
        hashed_password="hash",
        is_encrypted=True,
        encryption_salt=salt,
        challenge_blob="base64encodedblob==",
        argon2_params='{"time_cost":3,"memory_cost":65536,"parallelism":4}',
    )
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.username == "carol"))
    loaded = result.scalar_one()

    assert loaded.is_encrypted is True
    assert loaded.encryption_salt == salt
    assert loaded.challenge_blob == "base64encodedblob=="
    assert loaded.argon2_params == '{"time_cost":3,"memory_cost":65536,"parallelism":4}'


@pytest.mark.asyncio
async def test_is_encrypted_can_be_updated(db_session: AsyncSession) -> None:
    """User.is_encrypted can be toggled from False to True."""
    user = User(username="dave", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    assert user.is_encrypted is False

    user.is_encrypted = True
    await db_session.commit()
    await db_session.refresh(user)
    assert user.is_encrypted is True
