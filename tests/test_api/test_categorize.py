"""Tests for POST /api/categorize — Phase 4 (TDD red → green)."""

from httpx import AsyncClient


async def _setup_category(auth_client: AsyncClient, name: str = "Food") -> int:
    """Create a category group + category, return the category id."""
    group_resp = await auth_client.post(
        "/api/category-groups", json={"name": f"Group-{name}", "sort_order": 0}
    )
    assert group_resp.status_code == 201
    group_id = group_resp.json()["id"]

    cat_resp = await auth_client.post(
        "/api/categories",
        json={"group_id": group_id, "name": name, "sort_order": 0},
    )
    assert cat_resp.status_code == 201
    return int(cat_resp.json()["id"])


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------


async def test_categorize_requires_auth(client: AsyncClient) -> None:
    """Unauthenticated requests are rejected with 401."""
    resp = await client.post(
        "/api/categorize", json={"transactions": [{"payee_name": "Amazon"}]}
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


async def test_categorize_empty_list_rejected(auth_client: AsyncClient) -> None:
    """An empty transactions list fails Pydantic validation (min_length=1)."""
    resp = await auth_client.post("/api/categorize", json={"transactions": []})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# No-match
# ---------------------------------------------------------------------------


async def test_categorize_no_match(auth_client: AsyncClient) -> None:
    """Unknown payee, no rules → confidence 'none', category_id null."""
    resp = await auth_client.post(
        "/api/categorize",
        json={"transactions": [{"payee_name": "Unknown", "memo": None}]},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["category_id"] is None
    assert results[0]["confidence"] == "none"


# ---------------------------------------------------------------------------
# Payee auto-category
# ---------------------------------------------------------------------------


async def test_categorize_payee_match(auth_client: AsyncClient) -> None:
    """Payee with auto_category_id returns confidence 'auto'."""
    cat_id = await _setup_category(auth_client, "Groceries")

    # Create payee with auto category
    payee_resp = await auth_client.post(
        "/api/payees", json={"name": "Carrefour", "auto_category_id": cat_id}
    )
    assert payee_resp.status_code == 201

    resp = await auth_client.post(
        "/api/categorize",
        json={"transactions": [{"payee_name": "carrefour"}]},
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["category_id"] == cat_id
    assert result["confidence"] == "auto"


# ---------------------------------------------------------------------------
# Rule-based categorization
# ---------------------------------------------------------------------------


async def test_categorize_rule_contains(auth_client: AsyncClient) -> None:
    """A 'contains' rule on payee field returns confidence 'rule'."""
    cat_id = await _setup_category(auth_client, "Online")

    rule_resp = await auth_client.post(
        "/api/category-rules",
        json={
            "pattern": "amazon",
            "match_field": "payee",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": 5,
        },
    )
    assert rule_resp.status_code == 201

    resp = await auth_client.post(
        "/api/categorize",
        json={"transactions": [{"payee_name": "Amazon FR"}]},
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["category_id"] == cat_id
    assert result["confidence"] == "rule"


async def test_categorize_rule_memo(auth_client: AsyncClient) -> None:
    """A rule matching the memo field is applied when memo matches."""
    cat_id = await _setup_category(auth_client, "Rent")

    await auth_client.post(
        "/api/category-rules",
        json={
            "pattern": "loyer",
            "match_field": "memo",
            "match_type": "contains",
            "category_id": cat_id,
            "priority": 0,
        },
    )

    resp = await auth_client.post(
        "/api/categorize",
        json={"transactions": [{"payee_name": "VIREMENT", "memo": "paiement loyer"}]},
    )
    assert resp.status_code == 200
    result = resp.json()["results"][0]
    assert result["category_id"] == cat_id
    assert result["confidence"] == "rule"


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


async def test_categorize_batch_multiple(auth_client: AsyncClient) -> None:
    """Batch endpoint returns one result per input transaction, in order."""
    cat_id = await _setup_category(auth_client, "Streaming")

    await auth_client.post(
        "/api/payees", json={"name": "Netflix", "auto_category_id": cat_id}
    )

    resp = await auth_client.post(
        "/api/categorize",
        json={
            "transactions": [
                {"payee_name": "Netflix"},
                {"payee_name": "Unknown Shop"},
                {"payee_name": "netflix"},  # same payee, different case
            ]
        },
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 3
    assert results[0]["confidence"] == "auto"
    assert results[1]["confidence"] == "none"
    assert results[2]["confidence"] == "auto"  # case-insensitive


async def test_categorize_rule_isolation_between_users(
    auth_client: AsyncClient,
) -> None:
    """Rules created by alice are not applied to bob's categorization."""
    cat_id = await _setup_category(auth_client, "Alice-cat")

    await auth_client.post(
        "/api/category-rules",
        json={
            "pattern": "shared-shop",
            "match_field": "payee",
            "match_type": "exact",
            "category_id": cat_id,
            "priority": 0,
        },
    )

    # Register bob and obtain his token (re-using the same client)
    await auth_client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword1"}
    )
    login = await auth_client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword1"}
    )
    bob_token = login.json()["access_token"]

    # Temporarily use bob's token
    alice_header = auth_client.headers["Authorization"]
    auth_client.headers["Authorization"] = f"Bearer {bob_token}"

    resp = await auth_client.post(
        "/api/categorize",
        json={"transactions": [{"payee_name": "shared-shop"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["confidence"] == "none"

    # Restore
    auth_client.headers["Authorization"] = alice_header
