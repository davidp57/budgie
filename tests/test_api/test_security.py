"""Security tests — IDOR, input validation, and rate limiting.

Tests verify that:
- Users cannot access or modify resources owned by other users (IDOR).
- File uploads are rejected when the payload exceeds the size limit.
- Regex category rules with catastrophic-backtracking patterns are rejected.
- Budget/transaction month parameters are validated against YYYY-MM format.
"""

import io
from unittest.mock import patch

from httpx import AsyncClient

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
