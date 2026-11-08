"""Tests for the recurring payments API (subscriptions)."""

from __future__ import annotations

import datetime
from typing import Any

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _account(client: AsyncClient) -> int:
    resp = await client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _debit(
    client: AsyncClient, account_id: int, day: datetime.date, amount: int, memo: str
) -> None:
    resp = await client.post(
        "/api/transactions",
        json={
            "account_id": account_id,
            "date": day.isoformat(),
            "amount": -amount,
            "memo": memo,
            "status": "real",
            "import_hash": f"{memo}-{day.isoformat()}-{amount}",
        },
    )
    assert resp.status_code == 201, resp.text


async def _monthly(
    client: AsyncClient,
    account_id: int,
    memo: str,
    amount: int,
    count: int,
    start: datetime.date | None = None,
) -> None:
    # Recent dates, so that the subscription is active today.
    first = start or datetime.date.today() - datetime.timedelta(days=30 * (count - 1))
    for i in range(count):
        await _debit(
            client, account_id, first + datetime.timedelta(days=30 * i), amount, memo
        )


async def _classify(
    client: AsyncClient, candidate: dict[str, Any], kind: str = "subscription"
) -> dict[str, Any]:
    resp = await client.post(
        "/api/recurring",
        json={
            "key": candidate["key"],
            "name": "Streaming",
            "amount": candidate["amount"],
            "period": candidate["period"],
            "kind": kind,
        },
    )
    assert resp.status_code == 201, resp.text
    data: dict[str, Any] = resp.json()
    return data


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------


async def test_candidates_come_from_imported_debits(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "CARTE STREAMFLIX CB*12", 1399, 4)

    resp = await auth_client.get("/api/recurring/candidates")
    assert resp.status_code == 200
    [candidate] = resp.json()
    assert candidate["key"] == "STREAMFLIX"
    assert candidate["amount"] == 1399
    assert candidate["period"] == "monthly"
    assert candidate["monthly_cost"] == 1399
    assert candidate["occurrences"] == 4


async def test_manual_expenses_are_not_candidates(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    start = datetime.date.today() - datetime.timedelta(days=90)
    for i in range(4):
        resp = await auth_client.post(
            "/api/transactions",
            json={
                "account_id": acc,
                "date": (start + datetime.timedelta(days=30 * i)).isoformat(),
                "amount": -1399,
                "memo": "STREAMFLIX",
                "status": "real",
            },
        )
        assert resp.status_code == 201
    resp = await auth_client.get("/api/recurring/candidates")
    assert resp.json() == []


async def test_candidates_need_authentication(client: AsyncClient) -> None:
    resp = await client.get("/api/recurring/candidates")
    assert resp.status_code == 401


async def test_another_users_debits_never_show(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    alice_header = auth_client.headers["Authorization"]

    await client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword12"}
    )
    login = await client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword12"}
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    try:
        assert (await client.get("/api/recurring/candidates")).json() == []
        assert (await client.get("/api/recurring")).json()["payments"] == []
    finally:
        client.headers["Authorization"] = alice_header


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


async def test_a_classified_candidate_is_not_proposed_again(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()

    overview = await _classify(auth_client, candidate)
    [payment] = overview["payments"]
    assert payment["name"] == "Streaming"
    assert payment["kind"] == "subscription"
    assert payment["occurrences"] == 4
    assert payment["status"] == "active"
    assert (await auth_client.get("/api/recurring/candidates")).json() == []


async def test_forgetting_a_verdict_brings_the_candidate_back(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    overview = await _classify(auth_client, candidate, kind="dismissed")
    payment_id = overview["payments"][0]["id"]

    resp = await auth_client.delete(f"/api/recurring/{payment_id}")
    assert resp.status_code == 204
    assert len((await auth_client.get("/api/recurring/candidates")).json()) == 1


async def test_another_users_payment_cannot_be_changed(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]
    alice_header = auth_client.headers["Authorization"]

    await client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword12"}
    )
    login = await client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword12"}
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    try:
        resp = await client.patch(f"/api/recurring/{payment_id}", json={"name": "x"})
        assert resp.status_code == 404
        assert (await client.delete(f"/api/recurring/{payment_id}")).status_code == 404
    finally:
        client.headers["Authorization"] = alice_header


# ---------------------------------------------------------------------------
# Costs
# ---------------------------------------------------------------------------


async def test_the_total_mixes_periods_and_skips_other_payments(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1200, 4)
    today = datetime.date.today()
    for i in range(3):
        await _debit(
            auth_client,
            acc,
            today - datetime.timedelta(days=91 * i),
            3000,
            "PRLV SEPA EAU",
        )
    await _monthly(auth_client, acc, "PRLV SEPA IMPOTS", 50000, 4)

    for candidate in (await auth_client.get("/api/recurring/candidates")).json():
        kind = "other" if candidate["key"] == "IMPOTS" else "subscription"
        overview = await _classify(auth_client, candidate, kind=kind)

    assert overview["monthly_total"] == 1200 + 1000
    assert overview["yearly_total"] == (1200 + 1000) * 12


async def test_renaming_and_categorizing(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]
    group = await auth_client.post("/api/category-groups", json={"name": "Loisirs"})
    category = await auth_client.post(
        "/api/categories", json={"name": "Vidéo", "group_id": group.json()["id"]}
    )

    resp = await auth_client.patch(
        f"/api/recurring/{payment_id}",
        json={"name": "Films", "category_id": category.json()["id"]},
    )
    assert resp.status_code == 200
    [payment] = resp.json()["payments"]
    assert payment["name"] == "Films"
    assert payment["category_id"] == category.json()["id"]


async def test_an_unknown_category_is_refused(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]
    resp = await auth_client.patch(
        f"/api/recurring/{payment_id}", json={"category_id": 99999}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Cancellation and alerts
# ---------------------------------------------------------------------------


async def test_a_cancelled_subscription_leaves_the_total_and_reports_debits(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]
    cancelled = datetime.date.today() - datetime.timedelta(days=45)

    resp = await auth_client.patch(
        f"/api/recurring/{payment_id}", json={"cancelled_at": cancelled.isoformat()}
    )
    data = resp.json()
    [payment] = data["payments"]
    assert payment["status"] == "cancelled"
    assert data["monthly_total"] == 0
    assert len(payment["debits_after_cancellation"]) == 2
    assert data["attention_count"] == 1

    resp = await auth_client.patch(
        f"/api/recurring/{payment_id}", json={"cancelled_at": None}
    )
    assert resp.json()["payments"][0]["status"] == "active"


async def test_a_stopped_subscription_is_probably_ended(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    start = datetime.date.today() - datetime.timedelta(days=200)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4, start=start)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    overview = await _classify(auth_client, candidate)
    assert overview["payments"][0]["status"] == "probably_ended"
    assert overview["monthly_total"] == 0
    assert overview["attention_count"] == 1


async def test_a_price_increase_is_reported_and_can_be_accepted(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    start = datetime.date.today() - datetime.timedelta(days=150)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4, start=start)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]
    # A new price counts once it is billed twice, one period apart.
    for day in (120, 150):
        await _debit(
            auth_client, acc, start + datetime.timedelta(days=day), 1799, "STREAMFLIX"
        )

    [payment] = (await auth_client.get("/api/recurring")).json()["payments"]
    assert payment["price_changed"] is True
    assert payment["amount"] == 1399
    assert payment["current_amount"] == 1799
    assert payment["monthly_cost"] == 1799
    assert payment["occurrences"] == 6
    assert (await auth_client.get("/api/recurring/candidates")).json() == []

    resp = await auth_client.patch(
        f"/api/recurring/{payment_id}", json={"amount": 1799}
    )
    [payment] = resp.json()["payments"]
    assert payment["price_changed"] is False
    assert payment["occurrences"] == 6


# ---------------------------------------------------------------------------
# Merging labels (the bank or the merchant renamed a debit)
# ---------------------------------------------------------------------------


async def _renamed_subscription(client: AsyncClient) -> tuple[int, dict[str, Any]]:
    """Old label stopped 4 months ago, new label since: classify the new one."""
    acc = await _account(client)
    today = datetime.date.today()
    await _monthly(client, acc, "OLDSTREAM", 1399, 6, start=today - timedelta_days(330))
    await _monthly(client, acc, "NEWSTREAM", 1399, 4)
    candidates = (await client.get("/api/recurring/candidates")).json()
    new = next(c for c in candidates if c["key"] == "NEWSTREAM")
    old = next(c for c in candidates if c["key"] == "OLDSTREAM")
    payment_id = (await _classify(client, new))["payments"][0]["id"]
    return payment_id, old


def timedelta_days(days: int) -> datetime.timedelta:
    return datetime.timedelta(days=days)


async def test_a_candidate_merged_into_a_payment_counts_for_it(
    auth_client: AsyncClient,
) -> None:
    payment_id, old = await _renamed_subscription(auth_client)
    resp = await auth_client.post(
        f"/api/recurring/{payment_id}/aliases",
        json={"key": old["key"], "amount": old["amount"]},
    )
    assert resp.status_code == 200, resp.text
    [payment] = resp.json()["payments"]
    assert payment["occurrences"] == 10
    assert payment["status"] == "active"
    assert [(a["key"], a["amount"]) for a in payment["aliases"]] == [
        ("OLDSTREAM", 1399)
    ]
    assert (await auth_client.get("/api/recurring/candidates")).json() == []


async def test_detaching_a_label_brings_the_candidate_back(
    auth_client: AsyncClient,
) -> None:
    payment_id, old = await _renamed_subscription(auth_client)
    overview = (
        await auth_client.post(
            f"/api/recurring/{payment_id}/aliases",
            json={"key": old["key"], "amount": old["amount"]},
        )
    ).json()
    alias_id = overview["payments"][0]["aliases"][0]["id"]

    resp = await auth_client.delete(f"/api/recurring/{payment_id}/aliases/{alias_id}")
    assert resp.status_code == 200
    [payment] = resp.json()["payments"]
    assert payment["aliases"] == []
    assert payment["occurrences"] == 4
    keys = [
        c["key"] for c in (await auth_client.get("/api/recurring/candidates")).json()
    ]
    assert keys == ["OLDSTREAM"]


async def test_merging_two_payments_keeps_one_with_both_histories(
    auth_client: AsyncClient,
) -> None:
    payment_id, old = await _renamed_subscription(auth_client)
    overview = await _classify(auth_client, old)
    old_id = next(p["id"] for p in overview["payments"] if p["key"] == "OLDSTREAM")
    await auth_client.patch(f"/api/recurring/{payment_id}", json={"name": "Streaming"})

    resp = await auth_client.post(
        f"/api/recurring/{payment_id}/merge", json={"other_id": old_id}
    )
    assert resp.status_code == 200, resp.text
    [payment] = resp.json()["payments"]
    assert payment["id"] == payment_id
    assert payment["name"] == "Streaming"
    assert payment["occurrences"] == 10
    assert [a["key"] for a in payment["aliases"]] == ["OLDSTREAM"]
    assert (await auth_client.get("/api/recurring/candidates")).json() == []


async def test_merging_a_payment_with_itself_is_refused(
    auth_client: AsyncClient,
) -> None:
    payment_id, _ = await _renamed_subscription(auth_client)
    resp = await auth_client.post(
        f"/api/recurring/{payment_id}/merge", json={"other_id": payment_id}
    )
    assert resp.status_code == 404


async def test_another_users_payment_cannot_be_merged_or_detached(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    payment_id, old = await _renamed_subscription(auth_client)
    overview = (
        await auth_client.post(
            f"/api/recurring/{payment_id}/aliases",
            json={"key": old["key"], "amount": old["amount"]},
        )
    ).json()
    alias_id = overview["payments"][0]["aliases"][0]["id"]
    alice_header = auth_client.headers["Authorization"]

    await client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword12"}
    )
    login = await client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword12"}
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    try:
        bob_acc = await _account(client)
        await _monthly(client, bob_acc, "GYM", 2990, 4)
        [bob_candidate] = (await client.get("/api/recurring/candidates")).json()
        bob_id = (await _classify(client, bob_candidate))["payments"][0]["id"]

        attach = await client.post(
            f"/api/recurring/{payment_id}/aliases", json={"key": "GYM", "amount": 2990}
        )
        assert attach.status_code == 404
        steal = await client.post(
            f"/api/recurring/{bob_id}/merge", json={"other_id": payment_id}
        )
        assert steal.status_code == 404
        detach = await client.delete(f"/api/recurring/{payment_id}/aliases/{alias_id}")
        assert detach.status_code == 404
    finally:
        client.headers["Authorization"] = alice_header
    [payment] = (await auth_client.get("/api/recurring")).json()["payments"]
    assert len(payment["aliases"]) == 1


async def test_a_label_renamed_with_a_new_price_is_not_a_price_change(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    today = datetime.date.today()
    await _monthly(
        auth_client, acc, "OLDSTREAM", 999, 6, start=today - timedelta_days(330)
    )
    await _monthly(auth_client, acc, "NEWSTREAM", 1299, 4)
    candidates = (await auth_client.get("/api/recurring/candidates")).json()
    old = next(c for c in candidates if c["key"] == "OLDSTREAM")
    new = next(c for c in candidates if c["key"] == "NEWSTREAM")
    payment_id = (await _classify(auth_client, old))["payments"][0]["id"]

    resp = await auth_client.post(
        f"/api/recurring/{payment_id}/aliases",
        json={"key": new["key"], "amount": new["amount"]},
    )
    [payment] = resp.json()["payments"]
    assert payment["current_amount"] == 1299
    assert payment["monthly_cost"] == 1299
    assert payment["price_changed"] is False
    assert payment["occurrences"] == 10


async def test_accepting_a_new_price_on_a_merged_label_keeps_the_history(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    today = datetime.date.today()
    await _monthly(
        auth_client, acc, "OLDSTREAM", 999, 6, start=today - timedelta_days(330)
    )
    await _monthly(
        auth_client, acc, "NEWSTREAM", 1299, 3, start=today - timedelta_days(150)
    )
    candidates = (await auth_client.get("/api/recurring/candidates")).json()
    old = next(c for c in candidates if c["key"] == "OLDSTREAM")
    new = next(c for c in candidates if c["key"] == "NEWSTREAM")
    payment_id = (await _classify(auth_client, old))["payments"][0]["id"]
    await auth_client.post(
        f"/api/recurring/{payment_id}/aliases",
        json={"key": new["key"], "amount": new["amount"]},
    )
    # The renamed label then goes up, billed twice one month apart
    for day in (60, 30):
        await _debit(auth_client, acc, today - timedelta_days(day), 1499, "NEWSTREAM")

    [payment] = (await auth_client.get("/api/recurring")).json()["payments"]
    assert payment["price_changed"] is True
    assert payment["current_amount"] == 1499

    resp = await auth_client.post(f"/api/recurring/{payment_id}/accept-price")
    assert resp.status_code == 200, resp.text
    [payment] = resp.json()["payments"]
    assert payment["price_changed"] is False
    assert payment["amount"] == 999
    assert payment["occurrences"] == 11
    assert (await auth_client.get("/api/recurring/candidates")).json() == []


async def test_merging_a_label_already_on_the_payment_adds_nothing(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 4)
    [candidate] = (await auth_client.get("/api/recurring/candidates")).json()
    payment_id = (await _classify(auth_client, candidate))["payments"][0]["id"]

    resp = await auth_client.post(
        f"/api/recurring/{payment_id}/aliases",
        json={"key": "STREAMFLIX", "amount": 1399},
    )
    assert resp.status_code == 200
    assert resp.json()["payments"][0]["aliases"] == []
