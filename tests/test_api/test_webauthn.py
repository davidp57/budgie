"""Tests for WebAuthn endpoints (passkey registration and authentication)."""

from unittest.mock import MagicMock, patch

import pytest
from budgie.models.webauthn import WebAuthnCredential
from budgie.services.user import get_user_by_username
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _register_alice(client: AsyncClient) -> str:
    """Register alice and return her JWT token."""
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "alicepassword"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "alicepassword"},
    )
    token: str = login.json()["access_token"]
    return token


async def _make_credential(db: AsyncSession, user_id: int) -> WebAuthnCredential:
    """Insert a fake WebAuthn credential for a user."""
    cred = WebAuthnCredential(
        user_id=user_id,
        credential_id=b"fake-credential-id",
        public_key=b"fake-public-key",
        sign_count=0,
        name="Test key",
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return cred


# ── Credential list ───────────────────────────────────────────────────────────


async def test_list_credentials_empty(client: AsyncClient) -> None:
    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/auth/webauthn/credentials")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_credentials_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/auth/webauthn/credentials")
    assert resp.status_code == 401


# ── Registration begin ────────────────────────────────────────────────────────


async def test_register_begin_returns_options(client: AsyncClient) -> None:
    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.post("/api/auth/webauthn/register/begin")
    assert resp.status_code == 200
    data = resp.json()
    assert "options" in data
    opts = data["options"]
    assert "challenge" in opts
    assert opts["rp"]["id"] is not None


async def test_register_begin_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/auth/webauthn/register/begin")
    assert resp.status_code == 401


# ── Registration complete (mocked) ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_complete_saves_credential(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    # Prime a challenge so complete_registration can pop it
    await client.post("/api/auth/webauthn/register/begin")

    fake_result = MagicMock()
    fake_result.credential_id = b"cred-id-bytes"
    fake_result.credential_public_key = b"pub-key-bytes"
    fake_result.sign_count = 0

    with patch(
        "budgie.services.webauthn.webauthn.verify_registration_response",
        return_value=fake_result,
    ):
        resp = await client.post(
            "/api/auth/webauthn/register/complete",
            json={
                "credential": {"id": "abc", "type": "public-key"},
                "name": "My Phone",
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Phone"
    assert "id" in data
    assert "created_at" in data


# ── Credential deletion ───────────────────────────────────────────────────────


async def test_delete_credential(client: AsyncClient, db_session: AsyncSession) -> None:
    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    user = await get_user_by_username(db_session, "alice")
    assert user is not None
    cred = await _make_credential(db_session, user.id)

    resp = await client.delete(f"/api/auth/webauthn/credentials/{cred.id}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # List should be empty now
    resp2 = await client.get("/api/auth/webauthn/credentials")
    assert resp2.json() == []


async def test_delete_credential_not_found(client: AsyncClient) -> None:
    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.delete("/api/auth/webauthn/credentials/99999")
    assert resp.status_code == 404


async def test_delete_credential_other_user(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Alice cannot delete Bob's credential."""
    await client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "bobpassword1"},
    )

    bob = await get_user_by_username(db_session, "bob")
    assert bob is not None
    cred = await _make_credential(db_session, bob.id)

    token = await _register_alice(client)
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.delete(f"/api/auth/webauthn/credentials/{cred.id}")
    assert resp.status_code == 404


# ── Authentication begin ──────────────────────────────────────────────────────


async def test_authenticate_begin_no_credentials(client: AsyncClient) -> None:
    await _register_alice(client)

    resp = await client.post(
        "/api/auth/webauthn/authenticate/begin",
        json={"username": "alice"},
    )
    assert resp.status_code == 400
    assert "No passkeys" in resp.json()["detail"]


async def test_authenticate_begin_unknown_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/auth/webauthn/authenticate/begin",
        json={"username": "nobody"},
    )
    assert resp.status_code == 404


async def test_authenticate_begin_returns_options(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _register_alice(client)

    user = await get_user_by_username(db_session, "alice")
    assert user is not None
    await _make_credential(db_session, user.id)

    resp = await client.post(
        "/api/auth/webauthn/authenticate/begin",
        json={"username": "alice"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "options" in data
    assert "challenge" in data["options"]
