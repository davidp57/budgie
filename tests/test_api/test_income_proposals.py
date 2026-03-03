"""Tests for GET /api/budget/{month}/income-proposals endpoint."""

from httpx import AsyncClient


async def test_income_proposals_empty(auth_client: AsyncClient) -> None:
    """Returns empty proposals when no M-1 transactions exist."""
    response = await auth_client.get("/api/budget/2026-03/income-proposals")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-03"
    assert data["previous_month"] == "2026-02"
    assert data["threshold_centimes"] == 200_000
    assert data["proposals"] == []


async def test_income_proposals_returns_qualifying_transactions(
    auth_client: AsyncClient,
) -> None:
    """Only transactions from M-1 with amount >= threshold are returned."""
    account = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    account_id = account.json()["id"]

    # Salary in M-1 (2026-02) — above default threshold (200 000)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-02-28",
            "amount": 350_000,
            "memo": "Salary Feb",
        },
    )
    # Bonus in M-1 — above threshold
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-02-15",
            "amount": 250_000,
            "memo": "Bonus",
        },
    )
    # Small refund in M-1 — BELOW default threshold, must be excluded
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-02-10",
            "amount": 5_000,
            "memo": "Refund",
        },
    )
    # Transaction in current month M — must NOT appear in proposals
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-03-01",
            "amount": 400_000,
            "memo": "March income",
        },
    )

    response = await auth_client.get("/api/budget/2026-03/income-proposals")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-03"
    assert data["previous_month"] == "2026-02"
    assert len(data["proposals"]) == 2  # only salary + bonus

    # Ordered by amount descending
    amounts = [p["amount"] for p in data["proposals"]]
    assert amounts == [350_000, 250_000]

    # Each proposal has required fields
    first = data["proposals"][0]
    assert first["memo"] == "Salary Feb"
    assert first["account_id"] == account_id
    assert "transaction_id" in first
    assert "date" in first


async def test_income_proposals_custom_threshold(auth_client: AsyncClient) -> None:
    """Custom threshold_centimes query parameter filters correctly."""
    account = await auth_client.post(
        "/api/accounts",
        json={"name": "Savings", "account_type": "savings", "on_budget": True},
    )
    account_id = account.json()["id"]

    await auth_client.post(
        "/api/transactions",
        json={"account_id": account_id, "date": "2025-12-20", "amount": 150_000},
    )
    await auth_client.post(
        "/api/transactions",
        json={"account_id": account_id, "date": "2025-12-10", "amount": 50_000},
    )

    # Default threshold (200 000): nothing returns
    r_default = await auth_client.get("/api/budget/2026-01/income-proposals")
    assert r_default.json()["proposals"] == []

    # Lower threshold (50 000): both return
    r_low = await auth_client.get(
        "/api/budget/2026-01/income-proposals?threshold_centimes=50000"
    )
    assert len(r_low.json()["proposals"]) == 2

    # threshold_centimes in response reflects requested value
    assert r_low.json()["threshold_centimes"] == 50_000


async def test_income_proposals_january_wraps_to_december(
    auth_client: AsyncClient,
) -> None:
    """For January, M-1 is correctly computed as previous December."""
    response = await auth_client.get("/api/budget/2026-01/income-proposals")
    assert response.status_code == 200
    data = response.json()
    assert data["previous_month"] == "2025-12"


async def test_income_proposals_scoped_to_user(
    client: AsyncClient, auth_client: AsyncClient
) -> None:
    """Proposals only include transactions from the authenticated user's accounts."""
    # Register second user Eve and get her token
    await client.post(
        "/api/auth/register",
        json={"username": "eve", "password": "evepassword"},
    )
    eve_login = await client.post(
        "/api/auth/login",
        json={"username": "eve", "password": "evepassword"},
    )
    eve_token = eve_login.json()["access_token"]
    eve_headers = {"Authorization": f"Bearer {eve_token}"}

    # Eve creates an account and a large transaction in M-1
    eve_account = await client.post(
        "/api/accounts",
        headers=eve_headers,
        json={"name": "Eve Checking", "account_type": "checking", "on_budget": True},
    )
    await client.post(
        "/api/transactions",
        headers=eve_headers,
        json={
            "account_id": eve_account.json()["id"],
            "date": "2026-02-15",
            "amount": 500_000,
            "memo": "Eve salary",
        },
    )

    # auth_client (alice) should NOT see eve's transactions
    response = await auth_client.get("/api/budget/2026-03/income-proposals")
    assert response.status_code == 200
    assert response.json()["proposals"] == []
