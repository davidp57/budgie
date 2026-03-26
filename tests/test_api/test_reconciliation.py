"""Tests for the reconciliation API endpoints."""

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_account(client: AsyncClient, name: str = "Checking") -> int:
    resp = await client.post(
        "/api/accounts",
        json={"name": name, "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_transaction(
    client: AsyncClient,
    account_id: int,
    amount: int,
    import_hash: str | None = None,
    category_id: int | None = None,
    date: str = "2026-03-10",
    memo: str = "Test",
    status: str = "real",
) -> int:
    payload: dict = {
        "account_id": account_id,
        "date": date,
        "amount": amount,
        "memo": memo,
        "status": status,
        "import_hash": import_hash,
        "category_id": category_id,
    }
    resp = await client.post("/api/transactions", json=payload)
    assert resp.status_code == 201
    return resp.json()["id"]


# ---------------------------------------------------------------------------
# GET /api/reconciliation/view
# ---------------------------------------------------------------------------


async def test_get_view_empty(auth_client: AsyncClient) -> None:
    """Empty account returns empty view."""
    acc_id = await _create_account(auth_client)
    resp = await auth_client.get(
        "/api/reconciliation/view", params={"account_id": acc_id, "month": "2026-03"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["bank_txs"] == []
    assert data["expenses"] == []
    assert data["links"] == []
    assert data["suggestions"] == []


async def test_get_view_separates_bank_and_expense(auth_client: AsyncClient) -> None:
    """Bank txs and budget expenses are categorised correctly."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -5230, import_hash="abc123", memo="CARREFOUR"
    )
    exp_id = await _create_transaction(auth_client, acc_id, -5000, memo="Courses")

    resp = await auth_client.get(
        "/api/reconciliation/view", params={"account_id": acc_id, "month": "2026-03"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bank_txs"]) == 1
    assert data["bank_txs"][0]["id"] == bank_id
    assert len(data["expenses"]) == 1
    assert data["expenses"][0]["id"] == exp_id


async def test_get_view_unknown_account(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(
        "/api/reconciliation/view", params={"account_id": 9999, "month": "2026-03"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/reconciliation/link
# ---------------------------------------------------------------------------


async def test_create_link(auth_client: AsyncClient) -> None:
    """Linking sets reconciled_with_id on the expense."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -5230, import_hash="abc123"
    )
    exp_id = await _create_transaction(auth_client, acc_id, -5000)

    resp = await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp_id},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["bank_tx_id"] == bank_id
    assert data["expense_id"] == exp_id


async def test_create_link_adjusts_amount(auth_client: AsyncClient) -> None:
    """adjust_amount=True updates the expense amount."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -5230, import_hash="abc123"
    )
    exp_id = await _create_transaction(auth_client, acc_id, -5000)

    await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp_id, "adjust_amount": True},
    )

    # Confirm via view
    view = await auth_client.get(
        "/api/reconciliation/view", params={"account_id": acc_id, "month": "2026-03"}
    )
    linked_exp = next(e for e in view.json()["expenses"] if e["id"] == exp_id)
    assert linked_exp["amount"] == -5230


async def test_create_link_conflict(auth_client: AsyncClient) -> None:
    """Cannot link the same bank tx twice."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -1000, import_hash="abc123"
    )
    exp1_id = await _create_transaction(auth_client, acc_id, -1000, memo="Exp1")
    exp2_id = await _create_transaction(auth_client, acc_id, -900, memo="Exp2")

    await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp1_id},
    )
    resp = await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp2_id},
    )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# DELETE /api/reconciliation/link/{bank_tx_id}
# ---------------------------------------------------------------------------


async def test_delete_link(auth_client: AsyncClient) -> None:
    """Deleting a link clears reconciled_with_id."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -1000, import_hash="abc123"
    )
    exp_id = await _create_transaction(auth_client, acc_id, -1000)

    await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp_id},
    )
    resp = await auth_client.delete(f"/api/reconciliation/link/{bank_id}")
    assert resp.status_code == 204

    # Link should be gone from view
    view = await auth_client.get(
        "/api/reconciliation/view", params={"account_id": acc_id, "month": "2026-03"}
    )
    assert view.json()["links"] == []


# ---------------------------------------------------------------------------
# POST /api/reconciliation/cloture
# ---------------------------------------------------------------------------


async def test_cloture(auth_client: AsyncClient) -> None:
    """Clôture marks linked pairs as reconciled."""
    acc_id = await _create_account(auth_client)
    bank_id = await _create_transaction(
        auth_client, acc_id, -1000, import_hash="abc123"
    )
    exp_id = await _create_transaction(auth_client, acc_id, -1000)

    await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_id, "expense_id": exp_id},
    )

    resp = await auth_client.post(
        "/api/reconciliation/cloture",
        json={"account_id": acc_id, "month": "2026-03"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reconciled_count"] == 1
    assert data["linked_count"] == 1


async def test_cloture_unknown_account(auth_client: AsyncClient) -> None:
    resp = await auth_client.post(
        "/api/reconciliation/cloture",
        json={"account_id": 9999, "month": "2026-03"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_endpoints_require_auth(client: AsyncClient) -> None:
    """All endpoints must return 401 without authentication."""
    resp = await client.get(
        "/api/reconciliation/view", params={"account_id": 1, "month": "2026-03"}
    )
    assert resp.status_code == 401
