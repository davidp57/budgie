"""Tests for transaction API endpoints, including planned transaction logic."""

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
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == -5000
    assert data["status"] == "real"


async def test_create_planned_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-02-01",
            "amount": -12000,
            "memo": "Planned rent payment",
            "status": "planned",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "planned"


# ── transaction_status filter ──────────────────────────────────────────────


async def test_filter_real_transactions(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-10",
            "amount": -1000,
            "status": "real",
        },
    )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -2000,
            "status": "planned",
        },
    )

    resp = await auth_client.get("/api/transactions?transaction_status=real")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["status"] == "real"


async def test_filter_planned_transactions(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-10",
            "amount": -1000,
            "status": "real",
        },
    )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -2000,
            "status": "planned",
        },
    )

    resp = await auth_client.get("/api/transactions?transaction_status=planned")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["status"] == "planned"


# ── Planned unlinked endpoint ───────────────────────────────────────────────


async def test_list_planned_unlinked_empty(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/transactions/planned/unlinked")
    assert response.status_code == 200
    assert response.json() == []


async def test_list_planned_unlinked_returns_pending(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    # Create a planned transaction (unlinked)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-03-01",
            "amount": -9900,
            "status": "planned",
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
            "status": "real",
        },
    )

    resp = await auth_client.get("/api/transactions/planned/unlinked")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["memo"] == "City gym"
    assert items[0]["status"] == "planned"


# ── Planned match endpoint ──────────────────────────────────────────────────


async def test_match_planned_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    planned = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-04-01",
            "amount": -5000,
            "status": "planned",
            "memo": "Planned",
        },
    )
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-04-03",
            "amount": -5000,
            "status": "real",
            "memo": "Real",
        },
    )

    planned_id = planned.json()["id"]
    real_id = real.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/planned/match",
        json={"real_transaction_id": real_id, "planned_transaction_id": planned_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == real_id


async def test_match_marks_planned_reconciled(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)

    planned = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-05-01",
            "amount": -7500,
            "status": "planned",
        },
    )
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-05-02",
            "amount": -7500,
            "status": "real",
        },
    )

    planned_id = planned.json()["id"]
    real_id = real.json()["id"]

    await auth_client.post(
        "/api/transactions/planned/match",
        json={"real_transaction_id": real_id, "planned_transaction_id": planned_id},
    )

    # Planned should no longer appear in unlinked list
    unlinked = await auth_client.get("/api/transactions/planned/unlinked")
    assert unlinked.status_code == 200
    assert all(t["id"] != planned_id for t in unlinked.json())


async def test_match_not_found_real_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    planned = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-06-01",
            "amount": -1000,
            "status": "planned",
        },
    )
    planned_id = planned.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/planned/match",
        json={"real_transaction_id": 99999, "planned_transaction_id": planned_id},
    )
    assert resp.status_code == 404


async def test_match_not_found_planned_transaction(auth_client: AsyncClient) -> None:
    account_id = await _create_account(auth_client)
    real = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-06-02",
            "amount": -1000,
            "status": "real",
        },
    )
    real_id = real.json()["id"]

    resp = await auth_client.post(
        "/api/transactions/planned/match",
        json={"real_transaction_id": real_id, "planned_transaction_id": 99999},
    )
    assert resp.status_code == 400


# ── Scoping ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_planned_unlinked_scoped_to_user(
    client: AsyncClient, auth_client: AsyncClient
) -> None:
    """Planned transactions from another user must not appear."""
    account_id = await _create_account(auth_client)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-07-01",
            "amount": -3000,
            "status": "planned",
        },
    )

    # Register and auth as another user
    await client.post(
        "/api/auth/register",
        json={"username": "bob2", "password": "BobPassword2"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "bob2", "password": "BobPassword2"},
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    resp = await client.get("/api/transactions/planned/unlinked")
    assert resp.status_code == 200
    assert resp.json() == []


# ── PATCH (partial update) ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_transaction_category(auth_client: AsyncClient) -> None:
    """PATCH /transactions/{id} updates category_id."""
    account_id = await _create_account(auth_client)
    create_resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-15",
            "amount": -1500,
            "payee": "Supermarché",
        },
    )
    assert create_resp.status_code == 201
    txn_id = create_resp.json()["id"]

    # Create a category group + category to assign
    group_resp = await auth_client.post("/api/category-groups", json={"name": "Food"})
    assert group_resp.status_code == 201
    cat_resp = await auth_client.post(
        "/api/categories",
        json={"name": "Groceries", "group_id": group_resp.json()["id"]},
    )
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    patch_resp = await auth_client.patch(
        f"/api/transactions/{txn_id}",
        json={"category_id": cat_id},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["category_id"] == cat_id


@pytest.mark.asyncio
async def test_patch_transaction_not_found(auth_client: AsyncClient) -> None:
    """PATCH on a non-existent transaction returns 404."""
    resp = await auth_client.patch(
        "/api/transactions/99999", json={"category_id": None}
    )
    assert resp.status_code == 404


# ── Pagination (limit / offset) ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_transactions_with_limit(auth_client: AsyncClient) -> None:
    """GET /transactions?limit=N returns at most N results."""
    account_id = await _create_account(auth_client)
    for i in range(5):
        await auth_client.post(
            "/api/transactions",
            json={
                "account_id": account_id,
                "date": f"2024-01-{10 + i:02d}",
                "amount": -1000 * (i + 1),
            },
        )

    resp = await auth_client.get("/api/transactions?limit=3")
    assert resp.status_code == 200
    assert len(resp.json()) == 3


@pytest.mark.asyncio
async def test_list_transactions_with_offset(auth_client: AsyncClient) -> None:
    """GET /transactions?limit=2&offset=2 skips the first 2 rows."""
    account_id = await _create_account(auth_client)
    for i in range(5):
        await auth_client.post(
            "/api/transactions",
            json={
                "account_id": account_id,
                "date": f"2024-01-{10 + i:02d}",
                "amount": -1000 * (i + 1),
            },
        )

    # Without offset — first page
    page1 = await auth_client.get("/api/transactions?limit=2&offset=0")
    assert page1.status_code == 200
    assert len(page1.json()) == 2

    # Second page
    page2 = await auth_client.get("/api/transactions?limit=2&offset=2")
    assert page2.status_code == 200
    assert len(page2.json()) == 2

    # No overlap between pages
    ids1 = {t["id"] for t in page1.json()}
    ids2 = {t["id"] for t in page2.json()}
    assert ids1.isdisjoint(ids2)

    # Last page (only 1 remaining)
    page3 = await auth_client.get("/api/transactions?limit=2&offset=4")
    assert page3.status_code == 200
    assert len(page3.json()) == 1


@pytest.mark.asyncio
async def test_list_transactions_no_limit_returns_all(auth_client: AsyncClient) -> None:
    """GET /transactions without limit/offset returns all rows (backward compat)."""
    account_id = await _create_account(auth_client)
    for i in range(5):
        await auth_client.post(
            "/api/transactions",
            json={
                "account_id": account_id,
                "date": f"2024-01-{10 + i:02d}",
                "amount": -1000 * (i + 1),
            },
        )

    resp = await auth_client.get("/api/transactions")
    assert resp.status_code == 200
    assert len(resp.json()) == 5


# ── expenses_only filter ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_expenses_only_excludes_bank_imports(auth_client: AsyncClient) -> None:
    """GET /transactions?expenses_only=true returns only expense transactions."""
    account_id = await _create_account(auth_client)

    # Create a manual expense (no import_hash)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-10",
            "amount": -3000,
            "memo": "Grocery run",
        },
    )
    # Create a bank import (with import_hash)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -4500,
            "memo": "CARREFOUR",
            "import_hash": "abc123hash",
        },
    )

    resp = await auth_client.get("/api/transactions?expenses_only=true")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["memo"] == "Grocery run"
    assert items[0]["import_hash"] is None


@pytest.mark.asyncio
async def test_expenses_only_false_returns_all(auth_client: AsyncClient) -> None:
    """GET /transactions?expenses_only=false returns all transactions (default)."""
    account_id = await _create_account(auth_client)

    await auth_client.post(
        "/api/transactions",
        json={"account_id": account_id, "date": "2024-01-10", "amount": -1000},
    )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-01-11",
            "amount": -2000,
            "import_hash": "def456hash",
        },
    )

    resp = await auth_client.get("/api/transactions?expenses_only=false")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


@pytest.mark.asyncio
async def test_expenses_only_includes_linked_transaction(
    auth_client: AsyncClient,
) -> None:
    """When an expense is reconciled, linked_transaction is populated."""
    account_id = await _create_account(auth_client)

    # Create a bank import
    bank_resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-02-01",
            "amount": -5000,
            "memo": "LIDL achat",
            "import_hash": "bankhash99",
        },
    )
    bank_id = bank_resp.json()["id"]

    # Create a manual expense and reconcile it with the bank tx
    exp_resp = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2024-02-01",
            "amount": -5000,
            "memo": "Courses",
        },
    )
    exp_id = exp_resp.json()["id"]

    # Point the expense at the bank tx via reconciliation endpoint
    link_resp = await auth_client.post(
        "/api/reconciliation/link",
        json={"expense_id": exp_id, "bank_tx_id": bank_id},
    )
    assert link_resp.status_code in (200, 201)

    # Fetch expenses only — linked_transaction should be populated
    resp = await auth_client.get("/api/transactions?expenses_only=true")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert item["reconciled_with_id"] == bank_id
    assert item["linked_transaction"] is not None
    assert item["linked_transaction"]["memo"] == "LIDL achat"
    assert item["linked_transaction"]["amount"] == -5000
