"""Tests for the subscriptions presentation and the tag routes."""

from __future__ import annotations

import datetime
from typing import Any

from httpx import AsyncClient


async def _account(client: AsyncClient) -> int:
    resp = await client.post(
        "/api/accounts",
        json={"name": "Checking", "account_type": "checking", "on_budget": True},
    )
    assert resp.status_code == 201
    return int(resp.json()["id"])


async def _monthly(
    client: AsyncClient,
    account_id: int,
    memo: str,
    amount: int,
    count: int,
    end_days_ago: int = 0,
) -> None:
    today = datetime.date.today()
    for i in range(count):
        day = today - datetime.timedelta(days=end_days_ago + 30 * i)
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


async def _classify(
    client: AsyncClient,
    key: str,
    amount: int,
    kind: str = "subscription",
    name: str | None = None,
    cancelled_at: str | None = None,
) -> int:
    resp = await client.post(
        "/api/recurring",
        json={
            "key": key,
            "name": name or key.title(),
            "amount": amount,
            "period": "monthly",
            "kind": kind,
            "cancelled_at": cancelled_at,
        },
    )
    assert resp.status_code == 201, resp.text
    return next(p["id"] for p in resp.json()["payments"] if p["key"] == key)


def _item(summary: dict[str, Any], name: str) -> dict[str, Any]:
    return next(i for i in summary["items"] if i["name"] == name)


async def _login_bob(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword12"}
    )
    login = await client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword12"}
    )
    return f"Bearer {login.json()['access_token']}"


async def test_the_summary_lists_what_runs_and_was_kept(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV STREAMFLIX", 1399, 6)
    await _monthly(auth_client, acc, "VIR EPARGNE", 5000, 6)
    await _monthly(auth_client, acc, "PRLV OLDGYM", 2990, 6, end_days_ago=200)
    await _monthly(auth_client, acc, "PRLV CLOUD", 299, 6)
    await _monthly(auth_client, acc, "PRLV TELCO", 1999, 6)
    await _monthly(auth_client, acc, "PRLV MUSIC", 999, 6)
    await _classify(auth_client, "STREAMFLIX", 1399, name="Streaming")
    await _classify(auth_client, "EPARGNE", 5000, kind="other", name="Épargne")
    await _classify(auth_client, "OLDGYM", 2990)
    await _classify(auth_client, "CLOUD", 299, kind="dismissed")
    await _classify(
        auth_client,
        "TELCO",
        1999,
        cancelled_at=datetime.date.today().isoformat(),
    )

    summary = (await auth_client.get("/api/recurring/summary")).json()

    assert [i["name"] for i in summary["items"]] == ["Épargne", "Streaming"]
    assert summary["subscriptions_monthly"] == 1399
    assert summary["subscriptions_yearly"] == 1399 * 12
    assert summary["monthly_total"] == 1399 + 5000
    assert summary["yearly_total"] == (1399 + 5000) * 12
    # MUSIC is running and not classified yet: one line to confirm.
    assert summary["to_confirm_count"] == 1
    assert _item(summary, "Épargne")["kind"] == "other"


async def test_each_item_carries_its_history(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV STREAMFLIX", 1199, 3, end_days_ago=90)
    await _monthly(auth_client, acc, "PRLV STREAMFLIX", 1599, 3)
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    resp = await auth_client.post(
        "/api/recurring",
        json={
            "key": line["ref"]["key"],
            "name": "Streaming",
            "amount": line["ref"]["amount"],
            "period": line["ref"]["period"],
            "kind": "subscription",
        },
    )
    assert resp.status_code == 201

    summary = (await auth_client.get("/api/recurring/summary")).json()
    [item] = summary["items"]

    assert item["amount"] == 1599
    assert item["monthly_cost"] == 1599
    assert item["occurrences"] == 6
    assert len(item["debits"]) == 6
    # Most recent first
    assert item["debits"][0]["amount"] == 1599
    assert item["debits"][-1]["amount"] == 1199
    assert item["debits"][0]["date"] == item["last_date"]
    assert item["debits"][-1]["date"] == item["first_date"]
    assert [s["amount"] for s in item["segments"]] == [1199, 1599]
    assert item["tag_ids"] == []


async def test_tags_are_created_put_on_and_taken_off(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV STREAMFLIX", 1399, 6)
    payment_id = await _classify(auth_client, "STREAMFLIX", 1399)

    resp = await auth_client.post("/api/recurring/tags", json={"name": " Loisirs "})
    assert resp.status_code == 201
    tag = resp.json()
    assert tag["name"] == "Loisirs"
    again = await auth_client.post("/api/recurring/tags", json={"name": "loisirs"})
    assert again.json()["id"] == tag["id"]

    resp = await auth_client.put(f"/api/recurring/{payment_id}/tags/{tag['id']}")
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["items"][0]["tag_ids"] == [tag["id"]]
    assert summary["tags"] == [{"id": tag["id"], "name": "Loisirs"}]

    resp = await auth_client.delete(f"/api/recurring/{payment_id}/tags/{tag['id']}")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["tag_ids"] == []

    listed = (await auth_client.get("/api/recurring/tags")).json()
    assert listed == [{"id": tag["id"], "name": "Loisirs"}]

    resp = await auth_client.delete(f"/api/recurring/tags/{tag['id']}")
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


async def test_a_tag_name_cannot_be_blank(auth_client: AsyncClient) -> None:
    resp = await auth_client.post("/api/recurring/tags", json={"name": "   "})
    assert resp.status_code == 422


async def test_tags_and_summary_are_per_user(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV STREAMFLIX", 1399, 6)
    payment_id = await _classify(auth_client, "STREAMFLIX", 1399)
    tag = (
        await auth_client.post("/api/recurring/tags", json={"name": "Loisirs"})
    ).json()

    alice = auth_client.headers["Authorization"]
    auth_client.headers["Authorization"] = await _login_bob(auth_client)
    try:
        bob_tag = (
            await auth_client.post("/api/recurring/tags", json={"name": "Loisirs"})
        ).json()
        assert bob_tag["id"] != tag["id"]
        assert (await auth_client.get("/api/recurring/tags")).json() == [bob_tag]
        summary = (await auth_client.get("/api/recurring/summary")).json()
        assert summary["items"] == []

        put = f"/api/recurring/{payment_id}/tags/{bob_tag['id']}"
        assert (await auth_client.put(put)).status_code == 404
        delete = f"/api/recurring/{payment_id}/tags/{tag['id']}"
        assert (await auth_client.delete(delete)).status_code == 404
        tag_url = f"/api/recurring/tags/{tag['id']}"
        assert (await auth_client.delete(tag_url)).status_code == 404
    finally:
        auth_client.headers["Authorization"] = alice

    # Alice cannot use Bob's tag on her own payment either.
    put = f"/api/recurring/{payment_id}/tags/{bob_tag['id']}"
    assert (await auth_client.put(put)).status_code == 404
