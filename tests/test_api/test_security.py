"""Security tests — IDOR, input validation, and rate limiting.

Tests verify that:
- Users cannot access or modify resources owned by other users (IDOR).
- File uploads are rejected when the payload exceeds the size limit.
- Regex category rules with catastrophic-backtracking patterns are rejected.
- Budget/transaction month parameters are validated against YYYY-MM format.
"""

import datetime
import io
from unittest.mock import patch

from budgie.models.category_rule import CategoryRule
from budgie.models.transaction import Transaction
from budgie.models.user import User
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, username: str, password: str) -> str:
    """Register a user and return a JWT access token.

    Args:
        client: Base HTTP test client.
        username: Username to register.
        password: Password for the account.

    Returns:
        JWT access token string.
    """
    await client.post(
        "/api/auth/register", json={"username": username, "password": password}
    )
    login = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    return str(login.json()["access_token"])


async def _create_account(client: AsyncClient) -> int:
    """Create a checking account for the authenticated client and return its ID.

    Args:
        client: Authenticated HTTP test client.

    Returns:
        Account primary key.
    """
    resp = await client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _create_envelope(client: AsyncClient) -> int:
    """Create an envelope for the authenticated client and return its ID.

    Args:
        client: Authenticated HTTP test client.

    Returns:
        Envelope primary key.
    """
    resp = await client.post(
        "/api/envelopes",
        json={"name": "Food", "rollover": False, "sort_order": 0, "category_ids": []},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


# ---------------------------------------------------------------------------
# IDOR: POST /api/transactions
# ---------------------------------------------------------------------------


async def test_create_transaction_idor(client: AsyncClient) -> None:
    """User B cannot create a transaction in an account owned by user A."""
    token_a = await _register_and_login(client, "alice_tx", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_tx", "BobPassword1")

    # Alice creates an account
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_account_id = await _create_account(client)

    # Bob tries to create a transaction in Alice's account
    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.post(
        "/api/transactions",
        json={
            "account_id": alice_account_id,
            "date": "2026-01-01",
            "amount": -1000,
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# IDOR: PUT /api/budget/{month}  (upsert_allocation)
# ---------------------------------------------------------------------------


async def test_budget_allocation_idor(client: AsyncClient) -> None:
    """User B cannot modify allocations for an envelope owned by user A."""
    token_a = await _register_and_login(client, "alice_bgt", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_bgt", "BobPassword1")

    # Alice creates an envelope
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_envelope_id = await _create_envelope(client)

    # Bob tries to allocate budget to Alice's envelope
    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.put(
        "/api/budget/2026-01",
        json=[{"envelope_id": alice_envelope_id, "budgeted": 50000}],
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# IDOR: POST /api/imports/confirm
# ---------------------------------------------------------------------------


async def test_confirm_import_idor(client: AsyncClient) -> None:
    """User B cannot import transactions into an account owned by user A."""
    token_a = await _register_and_login(client, "alice_imp", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_imp", "BobPassword1")

    # Alice creates an account
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_account_id = await _create_account(client)

    # Bob tries to import into Alice's account (send a valid transaction body)
    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.post(
        "/api/imports/confirm",
        json={
            "account_id": alice_account_id,
            "transactions": [
                {
                    "date": "2026-01-01",
                    "amount": -1000,
                    "description": "Test",
                    "import_hash": "a" * 64,
                }
            ],
        },
    )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# IDOR: envelope categories — _set_categories user_id check
# ---------------------------------------------------------------------------


async def test_envelope_category_idor(client: AsyncClient) -> None:
    """User B cannot link categories owned by user A to their own envelope."""
    token_a = await _register_and_login(client, "alice_env", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_env", "BobPassword1")

    # Alice creates a category group + category
    client.headers["Authorization"] = f"Bearer {token_a}"
    grp_resp = await client.post(
        "/api/category-groups", json={"name": "Alice's Group", "sort_order": 0}
    )
    assert grp_resp.status_code == 201
    grp_id = grp_resp.json()["id"]
    cat_resp = await client.post(
        "/api/categories",
        json={"name": "Alice's Cat", "group_id": grp_id, "sort_order": 0},
    )
    assert cat_resp.status_code == 201
    alice_cat_id = cat_resp.json()["id"]
    alice_env_resp = await client.post(
        "/api/envelopes",
        json={
            "name": "Alice's Envelope",
            "rollover": False,
            "sort_order": 0,
            "category_ids": [alice_cat_id],
        },
    )
    assert alice_env_resp.status_code == 201
    alice_env_id = alice_env_resp.json()["id"]

    # Bob creates his own envelope and tries to link Alice's category
    client.headers["Authorization"] = f"Bearer {token_b}"
    bob_env_resp = await client.post(
        "/api/envelopes",
        json={
            "name": "Bob's Envelope",
            "rollover": False,
            "sort_order": 0,
            "category_ids": [alice_cat_id],
        },
    )
    assert bob_env_resp.status_code == 201
    # The category should NOT be linked (silently rejected)
    bob_env = bob_env_resp.json()
    linked_ids = [c["id"] for c in bob_env.get("categories", [])]
    assert alice_cat_id not in linked_ids

    # ...and Alice's own envelope must keep its category
    client.headers["Authorization"] = f"Bearer {token_a}"
    envelopes = (await client.get("/api/envelopes")).json()
    alice_env = next(e for e in envelopes if e["id"] == alice_env_id)
    assert [c["id"] for c in alice_env["categories"]] == [alice_cat_id]


# ---------------------------------------------------------------------------
# File upload size limit
# ---------------------------------------------------------------------------


async def test_upload_too_large(client: AsyncClient) -> None:
    """Uploading a file larger than the configured limit returns 413."""
    token = await _register_and_login(client, "upload_user", "UploadPassword1")
    client.headers["Authorization"] = f"Bearer {token}"

    # Generate a ~11 MB payload (larger than 10 MB default)
    large_content = b"x" * (11 * 1024 * 1024)
    resp = await client.post(
        "/api/imports/parse?file_format=csv",
        files={"file": ("big.csv", io.BytesIO(large_content), "text/csv")},
    )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# ReDoS protection — category rule regex validation
# ---------------------------------------------------------------------------


async def test_redos_regex_rejected(client: AsyncClient) -> None:
    """A regex pattern with catastrophic backtracking is rejected with 422."""
    token = await _register_and_login(client, "redos_user", "RedosPassword1")
    client.headers["Authorization"] = f"Bearer {token}"

    # Create a category to reference
    grp_resp = await client.post(
        "/api/category-groups", json={"name": "Test Group", "sort_order": 0}
    )
    grp_id = grp_resp.json()["id"]
    cat_resp = await client.post(
        "/api/categories",
        json={"name": "Test Cat", "group_id": grp_id, "sort_order": 0},
    )
    cat_id = cat_resp.json()["id"]

    # Pattern (a+)+ is a classic ReDoS pattern
    resp = await client.post(
        "/api/category-rules",
        json={
            "pattern": "(a+)+",
            "match_field": "memo",
            "match_type": "regex",
            "category_id": cat_id,
        },
    )
    assert resp.status_code == 422


async def test_invalid_regex_rejected(client: AsyncClient) -> None:
    """A syntactically invalid regex pattern is rejected with 422."""
    token = await _register_and_login(client, "badregex_user", "BadregexPassword1")
    client.headers["Authorization"] = f"Bearer {token}"

    grp_resp = await client.post(
        "/api/category-groups", json={"name": "Test Group", "sort_order": 0}
    )
    grp_id = grp_resp.json()["id"]
    cat_resp = await client.post(
        "/api/categories",
        json={"name": "Test Cat", "group_id": grp_id, "sort_order": 0},
    )
    cat_id = cat_resp.json()["id"]

    resp = await client.post(
        "/api/category-rules",
        json={
            "pattern": "(unclosed",
            "match_field": "memo",
            "match_type": "regex",
            "category_id": cat_id,
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Month parameter validation
# ---------------------------------------------------------------------------


async def test_budget_invalid_month_rejected(client: AsyncClient) -> None:
    """An invalid month string in the budget path returns 422."""
    token = await _register_and_login(client, "month_user", "MonthPassword1")
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/budget/not-a-month")
    assert resp.status_code == 422


async def test_budget_month_13_rejected(client: AsyncClient) -> None:
    """Month 13 is invalid and must return 422."""
    token = await _register_and_login(client, "month13_user", "Month13Password")
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/budget/2026-13")
    assert resp.status_code == 422


async def test_transactions_invalid_month_rejected(client: AsyncClient) -> None:
    """An invalid month query parameter on /api/transactions returns 422."""
    token = await _register_and_login(client, "txmonth_user", "TxmonthPassword1")
    client.headers["Authorization"] = f"Bearer {token}"

    resp = await client.get("/api/transactions?month=2026-13")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


async def test_security_headers_present(client: AsyncClient) -> None:
    """Every response must include the required security headers."""
    resp = await client.get("/api/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


# ---------------------------------------------------------------------------
# Registration guard
# ---------------------------------------------------------------------------


async def test_registration_disabled(client: AsyncClient) -> None:
    """When REGISTRATION_ENABLED=false, /register returns 403."""
    with patch("budgie.api.auth.settings") as mock_settings:
        mock_settings.registration_enabled = False
        resp = await client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "NewUserPassword1"},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Cross-user references: category / envelope / payee IDs sent by the client
# ---------------------------------------------------------------------------


async def _create_category(client: AsyncClient, name: str) -> int:
    """Create a category group + category for the authenticated client.

    Args:
        client: Authenticated HTTP test client.
        name: Category name.

    Returns:
        Category primary key.
    """
    grp = await client.post("/api/category-groups", json={"name": "G", "sort_order": 0})
    assert grp.status_code == 201
    cat = await client.post(
        "/api/categories",
        json={"name": name, "group_id": grp.json()["id"], "sort_order": 0},
    )
    assert cat.status_code == 201
    return int(cat.json()["id"])


def _rule_body(category_id: int, **overrides: object) -> dict[str, object]:
    """Return a valid rule creation body pointing at *category_id*.

    Args:
        category_id: Target category.
        **overrides: Fields replacing the defaults.

    Returns:
        JSON body for ``POST /api/category-rules``.
    """
    body: dict[str, object] = {
        "pattern": "SHOP",
        "match_field": "memo",
        "match_type": "contains",
        "category_id": category_id,
    }
    body.update(overrides)
    return body


async def test_create_rule_with_foreign_category_rejected(client: AsyncClient) -> None:
    """A rule cannot point at a category owned by another user."""
    token_a = await _register_and_login(client, "alice_rcat", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_rcat", "BobPassword1")
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_cat = await _create_category(client, "Lawyer")

    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.post("/api/category-rules", json=_rule_body(alice_cat))
    assert resp.status_code == 404


async def test_update_rule_with_foreign_category_rejected(client: AsyncClient) -> None:
    """A rule cannot be re-pointed at a category owned by another user."""
    token_a = await _register_and_login(client, "alice_rupd", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_rupd", "BobPassword1")
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_cat = await _create_category(client, "Lawyer")

    client.headers["Authorization"] = f"Bearer {token_b}"
    bob_cat = await _create_category(client, "Food")
    rule = await client.post("/api/category-rules", json=_rule_body(bob_cat))
    assert rule.status_code == 201
    rule_id = rule.json()["id"]
    resp = await client.put(
        f"/api/category-rules/{rule_id}", json={"category_id": alice_cat}
    )
    assert resp.status_code == 404
    stored = await client.get(f"/api/category-rules/{rule_id}")
    assert stored.json()["category_id"] == bob_cat


async def test_payee_with_foreign_auto_category_rejected(client: AsyncClient) -> None:
    """A payee cannot auto-assign a category owned by another user."""
    token_a = await _register_and_login(client, "alice_pcat", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_pcat", "BobPassword1")
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_cat = await _create_category(client, "Lawyer")

    client.headers["Authorization"] = f"Bearer {token_b}"
    resp = await client.post(
        "/api/payees", json={"name": "Shop", "auto_category_id": alice_cat}
    )
    assert resp.status_code == 404
    payee = await client.post("/api/payees", json={"name": "Shop"})
    assert payee.status_code == 201
    resp = await client.put(
        f"/api/payees/{payee.json()['id']}", json={"auto_category_id": alice_cat}
    )
    assert resp.status_code == 404


async def test_transaction_with_foreign_references_rejected(
    client: AsyncClient,
) -> None:
    """A transaction cannot reference another user's category, envelope or payee."""
    token_a = await _register_and_login(client, "alice_tref", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_tref", "BobPassword1")
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_refs = [
        {"category_id": await _create_category(client, "Lawyer")},
        {"envelope_id": await _create_envelope(client)},
        {
            "payee_id": (await client.post("/api/payees", json={"name": "P"})).json()[
                "id"
            ]
        },
    ]

    client.headers["Authorization"] = f"Bearer {token_b}"
    bob_account = await _create_account(client)
    base = {"account_id": bob_account, "date": "2026-01-15", "amount": -1000}
    for ref in alice_refs:
        resp = await client.post("/api/transactions", json={**base, **ref})
        assert resp.status_code == 404, ref

    txn = await client.post("/api/transactions", json=base)
    assert txn.status_code == 201
    for ref in alice_refs:
        resp = await client.put(f"/api/transactions/{txn.json()['id']}", json=ref)
        assert resp.status_code == 404, ref


async def test_transaction_update_with_own_references_allowed(
    auth_client: AsyncClient,
) -> None:
    """Re-sending one's own references, or clearing them, is still accepted."""
    cat = await _create_category(auth_client, "Food")
    env = await _create_envelope(auth_client)
    payee = (await auth_client.post("/api/payees", json={"name": "P"})).json()["id"]
    account = await _create_account(auth_client)
    refs = {"category_id": cat, "envelope_id": env, "payee_id": payee}
    txn = await auth_client.post(
        "/api/transactions",
        json={"account_id": account, "date": "2026-01-15", "amount": -1000, **refs},
    )
    assert txn.status_code == 201
    url = f"/api/transactions/{txn.json()['id']}"

    resp = await auth_client.put(url, json={**refs, "amount": -2000})
    assert resp.status_code == 200
    assert resp.json()["amount"] == -2000

    cleared = dict.fromkeys(refs)
    resp = await auth_client.put(url, json=cleared)
    assert resp.status_code == 200
    assert {k: resp.json()[k] for k in refs} == cleared


async def test_reconciliation_view_hides_foreign_category_names(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Names of another user's categories and envelopes never reach this view.

    The rule and the expense are written straight to the database, as rows
    stored before the API checked ownership would be.
    """
    token_a = await _register_and_login(client, "alice_rview", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_rview", "BobPassword1")
    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_cat = await _create_category(client, "Lawyer")
    alice_env_resp = await client.post(
        "/api/envelopes",
        json={
            "name": "Therapy",
            "rollover": False,
            "sort_order": 0,
            "category_ids": [],
        },
    )
    assert alice_env_resp.status_code == 201
    alice_env = alice_env_resp.json()["id"]

    client.headers["Authorization"] = f"Bearer {token_b}"
    bob_account = await _create_account(client)
    bob_id = await db_session.scalar(
        select(User.id).where(User.username == "bob_rview")
    )
    assert bob_id is not None
    view_params = {"account_id": bob_account, "month": "2026-01"}
    bank = await client.post(
        "/api/transactions",
        json={
            "account_id": bob_account,
            "date": "2026-01-15",
            "amount": -1000,
            "memo": "SHOP 42",
            "import_hash": "b" * 64,
        },
    )
    assert bank.status_code == 201

    # 1. A rule pointing at Alice's category: the bank line is a rule match
    db_session.add(
        CategoryRule(
            user_id=bob_id,
            pattern="SHOP",
            match_field="memo",
            match_type="contains",
            category_id=alice_cat,
        )
    )
    await db_session.commit()
    resp = await client.get("/api/reconciliation/view", params=view_params)
    assert resp.status_code == 200
    assert resp.json()["rule_matches"], "the bank line should match Bob's rule"
    assert "Lawyer" not in resp.text

    # 2. Expenses pointing at Alice's category and envelope: listed as expenses
    db_session.add_all(
        [
            Transaction(
                account_id=bob_account,
                date=datetime.date(2026, 1, 20),
                amount=-500,
                category_id=alice_cat,
            ),
            Transaction(
                account_id=bob_account,
                date=datetime.date(2026, 1, 21),
                amount=-700,
                envelope_id=alice_env,
            ),
        ]
    )
    await db_session.commit()
    resp = await client.get("/api/reconciliation/view", params=view_params)
    assert resp.status_code == 200
    assert len(resp.json()["expenses"]) == 2, "both expenses should be listed"
    assert "Lawyer" not in resp.text
    assert "Therapy" not in resp.text


# ---------------------------------------------------------------------------
# Regex validation on rule UPDATE (PUT /api/category-rules/{id})
# ---------------------------------------------------------------------------


async def test_update_rule_regex_validated(auth_client: AsyncClient) -> None:
    """A partial update cannot leave a rule with an invalid or ReDoS-prone regex."""
    cat = await _create_category(auth_client, "Food")
    # A contains rule may hold regex metacharacters: they are plain text there.
    contains = await auth_client.post(
        "/api/category-rules", json=_rule_body(cat, pattern="(unclosed")
    )
    regex = await auth_client.post(
        "/api/category-rules", json=_rule_body(cat, pattern="^SHOP", match_type="regex")
    )
    assert contains.status_code == 201
    assert regex.status_code == 201

    cases = [
        # switching only the match type turns the stored text into a regex
        (contains, {"match_type": "regex"}),
        (contains, {"match_type": "regex", "pattern": "(a+)+$"}),
        # changing only the pattern of a rule that already is a regex
        (regex, {"pattern": "(unclosed"}),
        (regex, {"pattern": "(a+)+$"}),
        # null for a NOT NULL column
        (regex, {"pattern": None}),
        # inverted amount range on the merged rule
        (regex, {"min_amount": 500, "max_amount": 100}),
    ]
    for rule, body in cases:
        resp = await auth_client.put(
            f"/api/category-rules/{rule.json()['id']}", json=body
        )
        assert resp.status_code == 422, body

    stored = await auth_client.get(f"/api/category-rules/{regex.json()['id']}")
    assert stored.json()["pattern"] == "^SHOP"
    stored = await auth_client.get(f"/api/category-rules/{contains.json()['id']}")
    assert stored.json()["match_type"] == "contains"


async def test_update_rule_pattern_length_aligned(auth_client: AsyncClient) -> None:
    """Update accepts no longer a pattern than creation does."""
    cat = await _create_category(auth_client, "Food")
    rule = await auth_client.post("/api/category-rules", json=_rule_body(cat))
    resp = await auth_client.put(
        f"/api/category-rules/{rule.json()['id']}", json={"pattern": "x" * 101}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Import deduplication is scoped to the account
# ---------------------------------------------------------------------------


async def test_import_dedup_scoped_to_account(client: AsyncClient) -> None:
    """The same bank line imports once into each account, not once overall."""
    line = {
        "date": "2026-01-01",
        "amount": -4200,
        "description": "SEPA DIRECT DEBIT POWER CO",
        "import_hash": "c" * 64,
    }
    token_a = await _register_and_login(client, "alice_dedup", "AlicePassword1")
    token_b = await _register_and_login(client, "bob_dedup", "BobPassword1")

    client.headers["Authorization"] = f"Bearer {token_a}"
    alice_account = await _create_account(client)
    resp = await client.post(
        "/api/imports/confirm",
        json={"account_id": alice_account, "transactions": [line]},
    )
    assert resp.json() == {"imported": 1, "duplicates": 0}

    client.headers["Authorization"] = f"Bearer {token_b}"
    bob_accounts = [await _create_account(client), await _create_account(client)]
    for account in bob_accounts:
        resp = await client.post(
            "/api/imports/confirm",
            json={"account_id": account, "transactions": [line]},
        )
        assert resp.json() == {"imported": 1, "duplicates": 0}

    # Re-importing into the same account is still deduplicated
    resp = await client.post(
        "/api/imports/confirm",
        json={"account_id": bob_accounts[0], "transactions": [line]},
    )
    assert resp.json() == {"imported": 0, "duplicates": 1}
