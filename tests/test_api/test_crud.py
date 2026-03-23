"""Tests for account CRUD endpoints."""

from httpx import AsyncClient


async def test_list_accounts_empty(auth_client: AsyncClient):
    response = await auth_client.get("/api/accounts")
    assert response.status_code == 200
    assert response.json() == []


async def test_create_account(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Checking"
    assert data["account_type"] == "checking"
    assert data["on_budget"] is True
    assert "id" in data


async def test_create_account_invalid_type(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/accounts",
        json={"name": "Test", "account_type": "invalid", "on_budget": True},
    )
    assert response.status_code == 422


async def test_get_account(auth_client: AsyncClient):
    created = await auth_client.post(
        "/api/accounts",
        json={"name": "Savings", "account_type": "savings", "on_budget": True},
    )
    account_id = created.json()["id"]
    response = await auth_client.get(f"/api/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Savings"


async def test_get_account_not_found(auth_client: AsyncClient):
    response = await auth_client.get("/api/accounts/9999")
    assert response.status_code == 404


async def test_update_account(auth_client: AsyncClient):
    created = await auth_client.post(
        "/api/accounts",
        json={"name": "Old Name", "account_type": "checking", "on_budget": True},
    )
    account_id = created.json()["id"]
    response = await auth_client.put(
        f"/api/accounts/{account_id}",
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


async def test_delete_account(auth_client: AsyncClient):
    created = await auth_client.post(
        "/api/accounts",
        json={"name": "To Delete", "account_type": "cash", "on_budget": False},
    )
    account_id = created.json()["id"]
    response = await auth_client.delete(f"/api/accounts/{account_id}")
    assert response.status_code == 204
    response = await auth_client.get(f"/api/accounts/{account_id}")
    assert response.status_code == 404


async def test_accounts_scoped_to_user(client: AsyncClient, auth_client: AsyncClient):
    """Accounts created by one user are not visible to another."""
    # Create second user and get their client
    await client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "bobspassword"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "bobspassword"},
    )
    bob_token = login.json()["access_token"]

    # alice creates an account
    await auth_client.post(
        "/api/accounts",
        json={"name": "Alice Account", "account_type": "checking", "on_budget": True},
    )

    # bob should see empty list
    response = await client.get(
        "/api/accounts",
        headers={"Authorization": f"Bearer {bob_token}"},
    )
    assert response.json() == []


# ── Category Groups ──────────────────────────────────────────────


async def test_create_category_group(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/category-groups",
        json={"name": "Bills", "sort_order": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bills"
    assert data["categories"] == []


async def test_list_category_groups(auth_client: AsyncClient):
    await auth_client.post(
        "/api/category-groups", json={"name": "Bills", "sort_order": 1}
    )
    await auth_client.post(
        "/api/category-groups", json={"name": "Food", "sort_order": 2}
    )
    response = await auth_client.get("/api/category-groups")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ── Categories ───────────────────────────────────────────────────


async def test_create_category(auth_client: AsyncClient):
    group = await auth_client.post(
        "/api/category-groups", json={"name": "Bills", "sort_order": 1}
    )
    group_id = group.json()["id"]
    response = await auth_client.post(
        "/api/categories",
        json={"name": "Electricity", "group_id": group_id, "sort_order": 1},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Electricity"


async def test_update_category(auth_client: AsyncClient):
    group = await auth_client.post(
        "/api/category-groups", json={"name": "Bills", "sort_order": 1}
    )
    group_id = group.json()["id"]
    cat = await auth_client.post(
        "/api/categories",
        json={"name": "Electricity", "group_id": group_id},
    )
    cat_id = cat.json()["id"]
    response = await auth_client.put(
        f"/api/categories/{cat_id}",
        json={"hidden": True},
    )
    assert response.status_code == 200
    assert response.json()["hidden"] is True


async def test_delete_category(auth_client: AsyncClient):
    group = await auth_client.post(
        "/api/category-groups", json={"name": "Bills", "sort_order": 1}
    )
    group_id = group.json()["id"]
    cat = await auth_client.post(
        "/api/categories",
        json={"name": "Electricity", "group_id": group_id},
    )
    cat_id = cat.json()["id"]
    response = await auth_client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 204


# ── Payees ───────────────────────────────────────────────────────


async def test_create_payee(auth_client: AsyncClient):
    response = await auth_client.post(
        "/api/payees",
        json={"name": "Carrefour"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Carrefour"


async def test_list_payees(auth_client: AsyncClient):
    await auth_client.post("/api/payees", json={"name": "Carrefour"})
    await auth_client.post("/api/payees", json={"name": "Amazon"})
    response = await auth_client.get("/api/payees")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ── Transactions ─────────────────────────────────────────────────


async def test_create_transaction(auth_client: AsyncClient):
    account = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    account_id = account.json()["id"]
    response = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": "2026-01-15",
            "amount": -5050,
            "cleared": "cleared",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == -5050
    assert data["date"] == "2026-01-15"


async def test_list_transactions_by_account(auth_client: AsyncClient):
    acct1 = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    acct2 = await auth_client.post(
        "/api/accounts",
        json={"name": "Savings", "account_type": "savings", "on_budget": True},
    )
    acct1_id = acct1.json()["id"]
    acct2_id = acct2.json()["id"]
    for i in range(3):
        await auth_client.post(
            "/api/transactions",
            json={
                "account_id": acct1_id,
                "date": f"2026-01-{10 + i:02d}",
                "amount": -1000 * (i + 1),
                "cleared": "uncleared",
            },
        )
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": acct2_id,
            "date": "2026-01-20",
            "amount": 100000,
            "cleared": "cleared",
        },
    )
    response = await auth_client.get(f"/api/transactions?account_id={acct1_id}")
    assert response.status_code == 200
    assert len(response.json()) == 3


async def test_update_transaction(auth_client: AsyncClient):
    acct = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    txn = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": acct.json()["id"],
            "date": "2026-01-15",
            "amount": -5050,
            "cleared": "uncleared",
        },
    )
    txn_id = txn.json()["id"]
    response = await auth_client.put(
        f"/api/transactions/{txn_id}",
        json={"status": "reconciled", "memo": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reconciled"
    assert response.json()["memo"] == "Updated"


async def test_delete_transaction(auth_client: AsyncClient):
    acct = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    txn = await auth_client.post(
        "/api/transactions",
        json={
            "account_id": acct.json()["id"],
            "date": "2026-01-15",
            "amount": -1000,
            "cleared": "uncleared",
        },
    )
    txn_id = txn.json()["id"]
    response = await auth_client.delete(f"/api/transactions/{txn_id}")
    assert response.status_code == 204


# ── Budget Allocations ───────────────────────────────────────────


async def test_set_budget_allocation(auth_client: AsyncClient):
    envelope = await auth_client.post("/api/envelopes", json={"name": "Bills"})
    env_id = envelope.json()["id"]
    response = await auth_client.put(
        "/api/budget/2026-01",
        json=[{"envelope_id": env_id, "budgeted": 15000}],
    )
    assert response.status_code == 200
    allocations = response.json()
    assert len(allocations) == 1
    assert allocations[0]["budgeted"] == 15000


async def test_get_budget_month(auth_client: AsyncClient) -> None:
    envelope = await auth_client.post("/api/envelopes", json={"name": "Bills"})
    env_id = envelope.json()["id"]
    await auth_client.put(
        "/api/budget/2026-01",
        json=[{"envelope_id": env_id, "budgeted": 20000}],
    )
    response = await auth_client.get("/api/budget/2026-01")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-01"
    assert "to_be_budgeted" in data
    assert "total_available" in data
    assert any(e["budgeted"] == 20000 for e in data["envelopes"])


async def test_get_budget_month_empty(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/budget/2026-06")
    assert response.status_code == 200
    data = response.json()
    assert data["month"] == "2026-06"
    assert data["to_be_budgeted"] == 0
    assert data["total_available"] == 0
    assert data["envelopes"] == []


async def test_get_budget_month_envelope_fields(auth_client: AsyncClient) -> None:
    """Envelope response includes budgeted, activity, available and names."""
    envelope = await auth_client.post(
        "/api/envelopes", json={"name": "Household", "rollover": False}
    )
    env_id = envelope.json()["id"]
    await auth_client.put(
        "/api/budget/2026-01",
        json=[{"envelope_id": env_id, "budgeted": 80000}],
    )
    response = await auth_client.get("/api/budget/2026-01")
    assert response.status_code == 200
    envelopes = response.json()["envelopes"]
    assert len(envelopes) == 1
    env = envelopes[0]
    assert env["envelope_id"] == env_id
    assert env["envelope_name"] == "Household"
    assert env["rollover"] is False
    assert env["budgeted"] == 80000
    assert env["activity"] == 0
    assert env["available"] == 80000


async def test_get_budget_month_to_be_budgeted(auth_client: AsyncClient) -> None:
    """to_be_budgeted reflects income minus total budgeted."""
    envelope = await auth_client.post("/api/envelopes", json={"name": "Bills"})
    account = await auth_client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    # Post income (uncategorised, positive)
    await auth_client.post(
        "/api/transactions",
        json={
            "account_id": account.json()["id"],
            "date": "2026-01-01",
            "amount": 300000,
            "category_id": None,
        },
    )
    await auth_client.put(
        "/api/budget/2026-01",
        json=[{"envelope_id": envelope.json()["id"], "budgeted": 100000}],
    )
    response = await auth_client.get("/api/budget/2026-01")
    assert response.status_code == 200
    assert response.json()["to_be_budgeted"] == 200000  # 300000 - 100000
    assert response.json()["total_available"] == 100000  # 0 budgeted available = 100000


async def test_create_envelope_with_categories(auth_client: AsyncClient) -> None:
    """Creating an envelope with category_ids returns group_name on categories.

    Regression test: the service must eagerly load Category.group so that
    _to_envelope_read() can access c.group.name without triggering async
    lazy-loading (which raises MissingGreenlet / 500 in production).
    """
    group = await auth_client.post("/api/category-groups", json={"name": "Household"})
    group_id = group.json()["id"]
    cat = await auth_client.post(
        "/api/categories", json={"group_id": group_id, "name": "Groceries"}
    )
    cat_id = cat.json()["id"]

    response = await auth_client.post(
        "/api/envelopes",
        json={"name": "Food", "category_ids": [cat_id]},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Food"
    assert len(data["categories"]) == 1
    assert data["categories"][0]["name"] == "Groceries"
    assert data["categories"][0]["group_name"] == "Household"
