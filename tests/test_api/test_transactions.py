"""Tests for transaction API endpoints, including virtual transaction logic."""

import pytest
from httpx import AsyncClient

# ── Helpers ────────────────────────────────────────────────────────────────


async def _create_account(client: AsyncClient) -> int:
    """Create a checking account and return its ID."""
    resp = await client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


# ── Basic transaction CRUD ──────────────────────────────────────────────────


async def test_list_transactions_empty(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/transactions")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_real_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-15",
            "amount": -5000,
            "memo": "Groceries",
            "is_virtual": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == -5000
    assert data["is_virtual"] is False
    assert data["virtual_linked_id"] is None


async def test_create_virtual_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-02-01",
            "amount": -12000,
            "memo": "Planned rent payment",
            "is_virtual": True,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_virtual"] is True
    assert data["cleared"] == "uncleared"


# ── is_virtual filter ──────────────────────────────────────────────────────


async def test_filter_real_transactions(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-10",
            "amount": -1000,
            "is_virtual": False,
        },
    )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -2000,
            "is_virtual": True,
        },
    )

    resp = await auth_client.get("/api/transactions?is_virtual=false")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["is_virtual"] is False


async def test_filter_virtual_transactions(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-10",
            "amount": -1000,
            "is_virtual": False,
        },
    )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -2000,
            "is_virtual": True,
        },
    )

    resp = await auth_client.get("/api/transactions?is_virtual=true")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["is_virtual"] is True


# ── Virtual unlinked endpoint ───────────────────────────────────────────────


async def test_list_virtual_unlinked_empty(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/transactions/virtual/unlinked")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_virtual_unlinked_returns_pending(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    # Create a virtual transaction (unlinked)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-03-01",
            "amount": -9900,
            "is_virtual": True,
            "memo": "City gym",
        },
    )
    # Create a real transaction (must not appear)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-03-02",
            "amount": -500,
            "is_virtual": False,
        },
    )

    resp = await auth_client.get("/api/transactions/virtual/unlinked")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["memo"] == "City gym"
    assert items[0]["is_virtual"] is True


# ── Virtual match endpoint ──────────────────────────────────────────────────


async def test_match_virtual_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    virtual = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-04-01",
            "amount": -5000,
            "is_virtual": True,
            "memo": "Planned",
        },
    )
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-04-03",
            "amount": -5000,
            "is_virtual": False,
            "memo": "Real",
        },
    )

    virtual_id = virtual.json()["id"]
    real_id = real.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/virtual/match",
        json={"real_transaction_id": real_id, "virtual_transaction_id": virtual_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == real_id
    assert data["virtual_linked_id"] == virtual_id


async def test_match_marks_virtual_reconciled(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    virtual = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-05-01",
            "amount": -7500,
            "is_virtual": True,
        },
    )
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-05-02",
            "amount": -7500,
            "is_virtual": False,
        },
    )

    virtual_id = virtual.json()["id"]
    real_id = real.json()["id"]

    await auth_client.post(
        "/api/transactions/virtual/match",
        json={"real_transaction_id": real_id, "virtual_transaction_id": virtual_id},
    )

    # Virtual should no longer appear in unlinked list
    unlinked = await auth_client.get("/api/transactions/virtual/unlinked")
    assert unlinked.status_code == 200
    assert all(t["id"] != virtual_id for t in unlinked.json())


async def test_match_not_found_real_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    virtual = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-06-01",
            "amount": -1000,
            "is_virtual": True,
        },
    )
    virtual_id = virtual.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/virtual/match",
        json={"real_transaction_id": 99999, "virtual_transaction_id": virtual_id},
    )
    assert resp.status_code == 404


async def test_match_not_found_virtual_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-06-02",
            "amount": -1000,
            "is_virtual": False,
        },
    )
    real_id = real.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/virtual/match",
        json={"real_transaction_id": real_id, "virtual_transaction_id": 99999},
    )
    assert resp.status_code == 400


# ── Scoping ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_virtual_unlinked_scoped_to_user(
    client: AsyncClient, auth_client: AsyncClient
) -> None:
    """Virtual transactions from another user must not appear."""
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-07-01",
            "amount": -3000,
            "is_virtual": True,
        },
    )

    # Register and auth as another user
    await client.post(
        "/api/auth/register",
        json={"username": "bob2", "password": "bobpassword2"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "bob2", "password": "bobpassword2"},
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    resp = await client.get("/api/transactions/virtual/unlinked")
    assert resp.status_code == 200
    assert resp.json() == []
