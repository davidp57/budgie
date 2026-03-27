"""Tests for the data reset endpoint (DELETE /api/user/reset)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_account(client: AsyncClient, name: str = "Checking") -> int:
    resp = await client.post(
        "/api/accounts",
        json={"name": name, "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _create_transaction(
    client: AsyncClient,
    account_id: int,
    amount: int = -1000,
    import_hash: str | None = None,
    date: str = "2026-03-10",
    memo: str = "Test",
) -> int:
    payload: dict[str, object] = {
        "account_id": account_id,
        "date": date,
        "amount": amount,
        "memo": memo,
        "status": "real",
        "import_hash": import_hash,
    }
    resp = await client.post("/api/transactions", json=payload)
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _create_category_rule(client: AsyncClient) -> int:
    # Create a group + category (required by the schema)
    grp_resp = await client.post(
        "/api/category-groups", json={"name": "ResetTestGroup", "sort_order": 0}
    )
    assert grp_resp.status_code == 201
    grp_id = int(grp_resp.json()["id"])

    cat_resp = await client.post(
        "/api/categories",
        json={"group_id": grp_id, "name": "ResetTestCat", "sort_order": 0},
    )
    assert cat_resp.status_code == 201
    cat_id = int(cat_resp.json()["id"])

    resp = await client.post(
        "/api/category-rules",
        json={
            "pattern": "SNCF",
            "match_field": "memo",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": 0,
        },
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


# ---------------------------------------------------------------------------
# DELETE /api/user/reset
# ---------------------------------------------------------------------------


async def test_reset_requires_authentication(client: AsyncClient) -> None:
    """Unauthenticated requests are rejected with 401."""
    resp = await client.delete("/api/user/reset")
    assert resp.status_code == 401


async def test_reset_empty_user_returns_zero_counts(auth_client: AsyncClient) -> None:
    """Reset on a user with no data returns zero counts."""
    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["transactions_deleted"] == 0
    assert body["rules_deleted"] == 0


async def test_reset_deletes_expenses(auth_client: AsyncClient) -> None:
    """Expenses (import_hash=None) are deleted; bank_txs are preserved."""
    acc_id = await _create_account(auth_client)
    # Two expenses
    await _create_transaction(auth_client, acc_id, amount=-500)
    await _create_transaction(auth_client, acc_id, amount=-1500)
    # One bank-imported transaction — must survive
    await _create_transaction(auth_client, acc_id, import_hash="keepme")

    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    assert resp.json()["transactions_deleted"] == 2

    # Only the bank_tx remains
    list_resp = await auth_client.get("/api/transactions")
    assert list_resp.status_code == 200
    remaining = list_resp.json()
    assert len(remaining) == 1
    assert remaining[0]["import_hash"] == "keepme"


async def test_reset_preserves_bank_imported_transactions(
    auth_client: AsyncClient,
) -> None:
    """Bank-imported transactions (import_hash set) are NOT deleted."""
    acc_id = await _create_account(auth_client)
    await _create_transaction(auth_client, acc_id, import_hash="abc123hash")
    await _create_transaction(auth_client, acc_id, import_hash="def456hash")

    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    assert resp.json()["transactions_deleted"] == 0

    # Both bank_txs still exist
    list_resp = await auth_client.get("/api/transactions")
    assert len(list_resp.json()) == 2


async def test_reset_deletes_expense_and_preserves_bank_tx(
    auth_client: AsyncClient,
) -> None:
    """Expense is deleted; linked bank_tx is preserved; no FK error raised."""
    acc_id = await _create_account(auth_client)
    bank_tx_id = await _create_transaction(
        auth_client, acc_id, amount=-1000, import_hash="bankhash1"
    )
    expense_id = await _create_transaction(auth_client, acc_id, amount=-1000)
    _ = expense_id  # created to carry the reconciled_with_id

    # Create reconciliation link (expense.reconciled_with_id = bank_tx.id)
    link_resp = await auth_client.post(
        "/api/reconciliation/link",
        json={"bank_tx_id": bank_tx_id, "expense_id": expense_id},
    )
    assert link_resp.status_code == 201

    # Reset: only the expense is deleted; bank_tx survives
    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    assert resp.json()["transactions_deleted"] == 1

    # bank_tx still present
    list_resp = await auth_client.get("/api/transactions")
    remaining = list_resp.json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == bank_tx_id


async def test_reset_deletes_category_rules(auth_client: AsyncClient) -> None:
    """All category rules for the authenticated user are deleted."""
    await _create_category_rule(auth_client)
    await _create_category_rule(auth_client)

    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    assert resp.json()["rules_deleted"] == 2

    # Verify rules are gone
    rules_resp = await auth_client.get("/api/category-rules")
    assert rules_resp.status_code == 200
    assert rules_resp.json() == []


async def test_reset_preserves_accounts(auth_client: AsyncClient) -> None:
    """Accounts are NOT deleted by the reset endpoint."""
    await _create_account(auth_client, name="My Checking")
    await _create_account(auth_client, name="My Savings")

    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200

    accounts_resp = await auth_client.get("/api/accounts")
    assert accounts_resp.status_code == 200
    assert len(accounts_resp.json()) == 2


async def test_reset_only_affects_current_user(
    client: AsyncClient,
    auth_client: AsyncClient,
) -> None:
    """Data belonging to another user is not deleted."""
    # Register a second user "bob" and create data
    await client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "bobpassword"},
    )
    bob_login = await client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "bobpassword"},
    )
    bob_token = bob_login.json()["access_token"]

    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    acc_resp = await client.post(
        "/api/accounts",
        json={"name": "Bob Checking", "account_type": "checking", "on_budget": True},
        headers=bob_headers,
    )
    assert acc_resp.status_code == 201
    bob_acc_id = acc_resp.json()["id"]

    tx_resp = await client.post(
        "/api/transactions",
        json={
            "account_id": bob_acc_id,
            "date": "2026-03-10",
            "amount": -500,
            "memo": "Bob tx",
            "status": "real",
        },
        headers=bob_headers,
    )
    assert tx_resp.status_code == 201

    # Create a category rule for Bob
    bob_grp = await client.post(
        "/api/category-groups",
        json={"name": "BobGroup", "sort_order": 0},
        headers=bob_headers,
    )
    assert bob_grp.status_code == 201
    bob_cat = await client.post(
        "/api/categories",
        json={"group_id": bob_grp.json()["id"], "name": "BobCat", "sort_order": 0},
        headers=bob_headers,
    )
    assert bob_cat.status_code == 201
    bob_rule = await client.post(
        "/api/category-rules",
        json={
            "pattern": "BOB-STORE",
            "match_field": "memo",
            "match_type": "contains",
            "category_id": bob_cat.json()["id"],
            "priority": 0,
        },
        headers=bob_headers,
    )
    assert bob_rule.status_code == 201

    # Now reset alice's data
    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200

    # Bob's transaction still exists
    bob_txs_resp = await client.get("/api/transactions", headers=bob_headers)
    assert bob_txs_resp.status_code == 200
    assert len(bob_txs_resp.json()) == 1

    # Bob's category rule still exists
    bob_rules_resp = await client.get("/api/category-rules", headers=bob_headers)
    assert bob_rules_resp.status_code == 200
    assert len(bob_rules_resp.json()) == 1


async def test_reset_returns_correct_counts(auth_client: AsyncClient) -> None:
    """Response body contains the exact counts of deleted items."""
    acc_id = await _create_account(auth_client)
    await _create_transaction(auth_client, acc_id, amount=-100)
    await _create_transaction(auth_client, acc_id, amount=-200)
    await _create_transaction(auth_client, acc_id, amount=-300)
    await _create_category_rule(auth_client)

    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["transactions_deleted"] == 3
    assert body["rules_deleted"] == 1


async def test_reset_deletes_split_transactions(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Split transactions are deleted before their parent expense on reset."""
    import datetime

    from budgie.models.account import Account
    from budgie.models.transaction import SplitTransaction, Transaction
    from budgie.models.user import User
    from sqlalchemy import select as sa_select

    # Retrieve the alice user and account from DB (created by auth_client fixture)
    user_row = (
        await db_session.execute(sa_select(User).where(User.username == "alice"))
    ).scalar_one()
    account = Account(
        user_id=user_row.id, name="Split Test", account_type="checking", on_budget=True
    )
    db_session.add(account)
    await db_session.flush()

    # Create a parent expense transaction directly in DB
    parent = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 3, 10),
        amount=-2000,
        memo="Supermarket",
        status="real",
    )
    db_session.add(parent)
    await db_session.flush()

    # Create two split transactions
    db_session.add(SplitTransaction(parent_id=parent.id, amount=-1200, memo="Food"))
    db_session.add(SplitTransaction(parent_id=parent.id, amount=-800, memo="Hygiene"))
    await db_session.flush()

    # Reset via API
    resp = await auth_client.delete("/api/user/reset")
    assert resp.status_code == 200
    assert resp.json()["transactions_deleted"] == 1

    # Parent and splits are all gone
    remaining_tx = (
        (
            await db_session.execute(
                sa_select(Transaction).where(Transaction.account_id == account.id)
            )
        )
        .scalars()
        .all()
    )
    assert remaining_tx == []

    remaining_splits = (
        (
            await db_session.execute(
                sa_select(SplitTransaction).where(
                    SplitTransaction.parent_id == parent.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert remaining_splits == []
