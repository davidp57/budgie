"""Tests for GET/PUT /api/users/me/preferences endpoint."""

from httpx import AsyncClient


async def test_get_preferences_default(auth_client: AsyncClient) -> None:
    """Newly created user has budget_mode = 'n1' by default."""
    response = await auth_client.get("/api/users/me/preferences")
    assert response.status_code == 200
    data = response.json()
    assert data["budget_mode"] == "n1"


async def test_update_preferences_to_n(auth_client: AsyncClient) -> None:
    """Can update budget_mode to 'n' (prévisionnel)."""
    response = await auth_client.put(
        "/api/users/me/preferences",
        json={"budget_mode": "n"},
    )
    assert response.status_code == 200
    assert response.json()["budget_mode"] == "n"

    # Verify persistence
    get_response = await auth_client.get("/api/users/me/preferences")
    assert get_response.json()["budget_mode"] == "n"


async def test_update_preferences_back_to_n1(auth_client: AsyncClient) -> None:
    """Can switch budget_mode back to 'n1'."""
    # First set to 'n'
    await auth_client.put("/api/users/me/preferences", json={"budget_mode": "n"})
    # Then switch back
    response = await auth_client.put(
        "/api/users/me/preferences",
        json={"budget_mode": "n1"},
    )
    assert response.status_code == 200
    assert response.json()["budget_mode"] == "n1"


async def test_update_preferences_invalid_mode(auth_client: AsyncClient) -> None:
    """Rejects invalid budget_mode values."""
    response = await auth_client.put(
        "/api/users/me/preferences",
        json={"budget_mode": "weekly"},
    )
    assert response.status_code == 422


async def test_preferences_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated requests are rejected with 401."""
    response = await client.get("/api/users/me/preferences")
    assert response.status_code == 401
