"""Tests for encryption setup and unlock endpoints."""

import pytest
from budgie.models.user import User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def _register_and_login(client: AsyncClient, username: str = "alice") -> str:
    """Helper: register a user and return a JWT token."""
    await client.post(
        "/api/auth/register",
        json={"username": username, "password": "SecurePass123"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": username, "password": "SecurePass123"},
    )
    return resp.json()["access_token"]


# ── POST /api/auth/setup-encryption ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_setup_encryption_sets_is_encrypted(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """After setup, user.is_encrypted is True."""
    token = await _register_and_login(client)
    resp = await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.username == "alice"))
    user = result.scalar_one()
    assert user.is_encrypted is True


@pytest.mark.asyncio
async def test_setup_encryption_stores_salt_and_blob(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """After setup, salt, challenge_blob and argon2_params are stored."""
    token = await _register_and_login(client)
    await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )

    result = await db_session.execute(select(User).where(User.username == "alice"))
    user = result.scalar_one()
    assert user.encryption_salt is not None
    assert len(user.encryption_salt) == 16
    assert user.challenge_blob is not None
    assert user.argon2_params is not None


@pytest.mark.asyncio
async def test_setup_encryption_returns_ok(client: AsyncClient) -> None:
    """Endpoint returns {"ok": true} on success."""
    token = await _register_and_login(client)
    resp = await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_setup_encryption_requires_auth(client: AsyncClient) -> None:
    """Endpoint requires a valid JWT."""
    resp = await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_setup_encryption_rejects_short_passphrase(client: AsyncClient) -> None:
    """Passphrase must be at least 8 characters."""
    token = await _register_and_login(client)
    resp = await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "short"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_setup_encryption_already_done_returns_409(client: AsyncClient) -> None:
    """Calling setup-encryption a second time returns 409."""
    token = await _register_and_login(client)
    await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 409


# ── POST /api/auth/unlock ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unlock_with_correct_passphrase_returns_ok(client: AsyncClient) -> None:
    """Correct passphrase returns {"ok": true}."""
    token = await _register_and_login(client)
    await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/auth/unlock",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_unlock_with_wrong_passphrase_returns_401(client: AsyncClient) -> None:
    """Wrong passphrase returns 401."""
    token = await _register_and_login(client)
    await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/auth/unlock",
        json={"passphrase": "wrong-passphrase"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unlock_without_setup_returns_400(client: AsyncClient) -> None:
    """Unlock before setup-encryption returns 400."""
    token = await _register_and_login(client)
    resp = await client.post(
        "/api/auth/unlock",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unlock_requires_auth(client: AsyncClient) -> None:
    """Unlock endpoint requires a valid JWT."""
    resp = await client.post(
        "/api/auth/unlock",
        json={"passphrase": "correct-horse-battery"},
    )
    assert resp.status_code == 401


# ── login flags after setup ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_after_setup_has_needs_setup_false_and_is_encrypted_true(
    client: AsyncClient,
) -> None:
    """After setup, login returns needs_encryption_setup=False and is_encrypted=True."""
    token = await _register_and_login(client)
    await client.post(
        "/api/auth/setup-encryption",
        json={"passphrase": "correct-horse-battery"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "SecurePass123"},
    )
    data = resp.json()
    assert data["needs_encryption_setup"] is False
    assert data["is_encrypted"] is True
