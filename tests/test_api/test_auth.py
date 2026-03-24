"""Tests for authentication endpoints (register, login, JWT protection)."""

from httpx import AsyncClient


async def test_register_creates_user(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "alice"
    assert "id" in data
    assert "hashed_password" not in data


async def test_register_duplicate_username(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    response = await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "anotherpass123"},
    )
    assert response.status_code == 409


async def test_register_weak_password(client: AsyncClient):
    response = await client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "short"},
    )
    assert response.status_code == 422


async def test_login_returns_token(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_returns_needs_encryption_setup_true_for_new_user(
    client: AsyncClient,
):
    """New users (is_encrypted=False) must get needs_encryption_setup=True."""
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["needs_encryption_setup"] is True


async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    response = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrongpassword"},
    )
    assert response.status_code == 401


async def test_login_unknown_user(client: AsyncClient):
    response = await client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "securepass123"},
    )
    assert response.status_code == 401


async def test_protected_route_requires_auth(client: AsyncClient):
    response = await client.get("/api/accounts")
    assert response.status_code == 401


async def test_protected_route_with_valid_token(client: AsyncClient):
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "securepass123"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "securepass123"},
    )
    token = login.json()["access_token"]
    response = await client.get(
        "/api/accounts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


async def test_protected_route_with_invalid_token(client: AsyncClient):
    response = await client.get(
        "/api/accounts",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
