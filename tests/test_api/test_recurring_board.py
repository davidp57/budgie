"""Tests for the subscriptions board, line links and reset."""

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


def _line(board: dict[str, Any], key: str) -> dict[str, Any]:
    return next(line for line in board["lines"] if line["key"] == key)


async def _login_bob(client: AsyncClient) -> str:
    await client.post(
        "/api/auth/register", json={"username": "bob", "password": "BobPassword12"}
    )
    login = await client.post(
        "/api/auth/login", json={"username": "bob", "password": "BobPassword12"}
    )
    return f"Bearer {login.json()['access_token']}"


async def test_the_board_answers_before_any_classification(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "CARTE STREAMFLIX CB*1", 1399, 6)
    await _monthly(auth_client, acc, "PRLV SEPA MUSIC", 999, 6)
    await _monthly(auth_client, acc, "VIR SEPA EPARGNE", 30000, 6)
    await _monthly(auth_client, acc, "PRLV SEPA OLDGYM", 2990, 6, end_days_ago=200)

    board = (await auth_client.get("/api/recurring/board")).json()
    assert board["monthly_total"] == 1399 + 999
    assert board["yearly_total"] == (1399 + 999) * 12
    assert board["estimated_count"] == 2
    assert _line(board, "EPARGNE")["likely_other"] is True
    assert _line(board, "OLDGYM")["running"] is False
    assert _line(board, "STREAMFLIX")["payment"] is None


async def test_successive_prices_are_one_line(auth_client: AsyncClient) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAM", 1199, 4, end_days_ago=120)
    await _monthly(auth_client, acc, "STREAM", 1599, 4)
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    assert [s["amount"] for s in line["segments"]] == [1199, 1599]
    assert line["amount"] == 1599
    assert line["running"] is True


async def test_classifying_other_takes_a_line_out_of_the_total(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 6)
    board = (await auth_client.get("/api/recurring/board")).json()
    ref = _line(board, "STREAMFLIX")["ref"]
    await auth_client.post(
        "/api/recurring",
        json={**ref, "name": "Streamflix", "kind": "other"},
    )
    board = (await auth_client.get("/api/recurring/board")).json()
    assert board["monthly_total"] == 0
    line = _line(board, "STREAMFLIX")
    assert line["payment"]["kind"] == "other"
    assert len(line["segments"]) == 1


async def test_a_renamed_label_is_suggested_and_linked(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV SEPA OLDNAME", 1918, 5, end_days_ago=150)
    await _monthly(auth_client, acc, "PRLV SEPA NEWNAME", 1918, 5)
    await _monthly(auth_client, acc, "PRLV SEPA OTHER", 1999, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    old, new = _line(board, "OLDNAME"), _line(board, "NEWNAME")
    assert board["suggestions"] == [{"earlier_id": old["id"], "later_id": new["id"]}]

    resp = await auth_client.post(
        "/api/recurring/link", json={"earlier": old["ref"], "later": new["ref"]}
    )
    assert resp.status_code == 200, resp.text
    board = resp.json()
    line = _line(board, "NEWNAME")
    assert line["payment"]["kind"] == "subscription"
    assert line["payment"]["occurrences"] == 10
    assert [a["key"] for a in line["payment"]["aliases"]] == ["OLDNAME"]
    assert line["first_date"] == old["first_date"]
    assert not any(line["key"] == "OLDNAME" for line in board["lines"])
    assert board["suggestions"] == []


async def test_linking_two_classified_lines_merges_them(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "OLDNAME", 999, 5, end_days_ago=200)
    await _monthly(auth_client, acc, "NEWNAME", 1299, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    for key in ("OLDNAME", "NEWNAME"):
        ref = _line(board, key)["ref"]
        await auth_client.post(
            "/api/recurring", json={**ref, "name": key.title(), "kind": "subscription"}
        )
    board = (await auth_client.get("/api/recurring/board")).json()
    old, new = _line(board, "OLDNAME"), _line(board, "NEWNAME")

    resp = await auth_client.post(
        "/api/recurring/link", json={"earlier": old["ref"], "later": new["ref"]}
    )
    assert resp.status_code == 200
    payments = [line for line in resp.json()["lines"] if line["payment"]]
    assert len(payments) == 1
    assert payments[0]["payment"]["occurrences"] == 10
    assert payments[0]["payment"]["price_changed"] is False


async def test_linking_another_users_payment_is_refused(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    ref = _line(board, "STREAMFLIX")["ref"]
    created = await auth_client.post(
        "/api/recurring", json={**ref, "name": "S", "kind": "subscription"}
    )
    alice_payment = created.json()["payments"][0]["id"]
    alice_header = auth_client.headers["Authorization"]

    client.headers["Authorization"] = await _login_bob(client)
    try:
        bob_acc = await _account(client)
        await _monthly(client, bob_acc, "GYM", 2990, 5)
        bob_ref = _line((await client.get("/api/recurring/board")).json(), "GYM")["ref"]
        resp = await client.post(
            "/api/recurring/link",
            json={"earlier": {"payment_id": alice_payment}, "later": bob_ref},
        )
        assert resp.status_code == 404
        resp = await client.post(
            "/api/recurring/link",
            json={"earlier": bob_ref, "later": {"payment_id": alice_payment}},
        )
        assert resp.status_code == 404
    finally:
        client.headers["Authorization"] = alice_header
    board = (await auth_client.get("/api/recurring/board")).json()
    assert _line(board, "STREAMFLIX")["payment"]["aliases"] == []


async def test_reset_forgets_classifications_and_keeps_transactions(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    ref = _line(board, "STREAMFLIX")["ref"]
    await auth_client.post(
        "/api/recurring", json={**ref, "name": "S", "kind": "dismissed"}
    )
    alice_header = auth_client.headers["Authorization"]

    # Bob's classification must survive Alice's reset
    bob_header = await _login_bob(client)
    client.headers["Authorization"] = bob_header
    bob_acc = await _account(client)
    await _monthly(client, bob_acc, "GYM", 2990, 5)
    bob_ref = _line((await client.get("/api/recurring/board")).json(), "GYM")["ref"]
    await client.post(
        "/api/recurring", json={**bob_ref, "name": "G", "kind": "subscription"}
    )
    client.headers["Authorization"] = alice_header

    resp = await auth_client.delete("/api/recurring")
    assert resp.status_code == 200
    assert _line(resp.json(), "STREAMFLIX")["payment"] is None
    txns = await auth_client.get("/api/transactions", params={"account_id": acc})
    assert len(txns.json()) == 5

    client.headers["Authorization"] = bob_header
    try:
        bob_line = _line((await client.get("/api/recurring/board")).json(), "GYM")
        assert bob_line["payment"] is not None
    finally:
        client.headers["Authorization"] = alice_header


async def test_a_line_can_be_declared_cancelled_when_classified(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 6)
    board = (await auth_client.get("/api/recurring/board")).json()
    ref = _line(board, "STREAMFLIX")["ref"]
    cancelled = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
    await auth_client.post(
        "/api/recurring",
        json={**ref, "name": "S", "kind": "subscription", "cancelled_at": cancelled},
    )
    board = (await auth_client.get("/api/recurring/board")).json()
    payment = _line(board, "STREAMFLIX")["payment"]
    assert payment["status"] == "cancelled"
    assert payment["cancelled_at"] == cancelled
    assert len(payment["debits_after_cancellation"]) == 2
    assert board["monthly_total"] == 0


async def test_the_board_is_as_of_the_last_imported_debit(
    auth_client: AsyncClient,
) -> None:
    """Statements imported months ago must not make everything look stopped."""
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "STREAMFLIX", 1399, 6, end_days_ago=250)
    await _monthly(auth_client, acc, "OLDGYM", 2990, 4, end_days_ago=400)
    board = (await auth_client.get("/api/recurring/board")).json()
    last = (datetime.date.today() - datetime.timedelta(days=250)).isoformat()
    assert board["as_of"] == last
    assert _line(board, "STREAMFLIX")["running"] is True
    assert _line(board, "OLDGYM")["running"] is False
    assert board["monthly_total"] == 1399


async def test_an_empty_board_is_as_of_today(auth_client: AsyncClient) -> None:
    board = (await auth_client.get("/api/recurring/board")).json()
    assert board["as_of"] == datetime.date.today().isoformat()
    assert board["lines"] == []


async def _debits_on(
    client: AsyncClient, account_id: int, memo: str, amount: int, days_ago: list[int]
) -> None:
    today = datetime.date.today()
    for d in days_ago:
        day = today - datetime.timedelta(days=d)
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


async def test_confirming_a_line_keeps_its_older_prices_despite_a_gap(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    # 9.99 for 6 months, one month without debit, then 13.49 for 5 months
    await _debits_on(auth_client, acc, "STREAM", 999, [360, 330, 300, 270, 240, 210])
    await _debits_on(auth_client, acc, "STREAM", 1349, [150, 120, 90, 60, 30])
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    assert len(line["segments"]) == 2

    resp = await auth_client.post(
        "/api/recurring", json={**line["ref"], "name": "Stream", "kind": "subscription"}
    )
    assert resp.status_code == 201
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    assert line["payment"]["occurrences"] == 11
    assert len(line["segments"]) == 2


async def test_confirming_a_line_that_went_yearly_keeps_its_monthly_past(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    # Monthly for a year, then yearly right after
    await _debits_on(auth_client, acc, "SOFT", 999, [1060 - 30 * i for i in range(12)])
    await _debits_on(auth_client, acc, "SOFT", 9999, [700, 335])
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    assert line["period"] == "yearly"

    await auth_client.post(
        "/api/recurring", json={**line["ref"], "name": "Soft", "kind": "subscription"}
    )
    board = (await auth_client.get("/api/recurring/board")).json()
    [line] = board["lines"]
    assert line["payment"]["occurrences"] == 14


async def test_linking_a_classified_line_to_its_new_label_keeps_its_settings(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV SEPA OLDNAME", 1918, 5, end_days_ago=150)
    await _monthly(auth_client, acc, "PRLV SEPA NEWNAME", 1918, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    old_ref = _line(board, "OLDNAME")["ref"]
    created = await auth_client.post(
        "/api/recurring", json={**old_ref, "name": "Mon service", "kind": "other"}
    )
    payment_id = created.json()["payments"][0]["id"]
    board = (await auth_client.get("/api/recurring/board")).json()
    old, new = _line(board, "OLDNAME"), _line(board, "NEWNAME")

    resp = await auth_client.post(
        "/api/recurring/link", json={"earlier": old["ref"], "later": new["ref"]}
    )
    assert resp.status_code == 200
    classified = [line for line in resp.json()["lines"] if line["payment"]]
    assert len(classified) == 1
    payment = classified[0]["payment"]
    assert payment["id"] == payment_id
    assert payment["name"] == "Mon service"
    assert payment["kind"] == "other"
    assert payment["occurrences"] == 10
    assert len(resp.json()["lines"]) == 1


async def test_a_refused_suggestion_does_not_come_back_until_reset(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV SEPA OLDNAME", 1918, 5, end_days_ago=150)
    await _monthly(auth_client, acc, "PRLV SEPA NEWNAME", 1918, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    assert len(board["suggestions"]) == 1

    resp = await auth_client.post(
        "/api/recurring/link/refuse",
        json={"earlier_key": "OLDNAME", "later_key": "NEWNAME"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["suggestions"] == []
    assert (await auth_client.get("/api/recurring/board")).json()["suggestions"] == []

    # Classifying one of the lines does not bring the refused suggestion back
    new_ref = _line(board, "NEWNAME")["ref"]
    await auth_client.post(
        "/api/recurring", json={**new_ref, "name": "New", "kind": "subscription"}
    )
    assert (await auth_client.get("/api/recurring/board")).json()["suggestions"] == []

    reset = await auth_client.delete("/api/recurring")
    assert len(reset.json()["suggestions"]) == 1


async def test_another_users_refusal_does_not_hide_my_suggestion(
    auth_client: AsyncClient, client: AsyncClient
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV SEPA OLDNAME", 1918, 5, end_days_ago=150)
    await _monthly(auth_client, acc, "PRLV SEPA NEWNAME", 1918, 5)
    alice_header = auth_client.headers["Authorization"]
    client.headers["Authorization"] = await _login_bob(client)
    try:
        resp = await client.post(
            "/api/recurring/link/refuse",
            json={"earlier_key": "OLDNAME", "later_key": "NEWNAME"},
        )
        assert resp.status_code == 200
    finally:
        client.headers["Authorization"] = alice_header
    board = (await auth_client.get("/api/recurring/board")).json()
    assert len(board["suggestions"]) == 1


async def test_the_board_counts_refusals_so_that_they_can_be_reset(
    auth_client: AsyncClient,
) -> None:
    acc = await _account(auth_client)
    await _monthly(auth_client, acc, "PRLV SEPA OLDNAME", 1918, 5, end_days_ago=150)
    await _monthly(auth_client, acc, "PRLV SEPA NEWNAME", 1918, 5)
    board = (await auth_client.get("/api/recurring/board")).json()
    assert board["refused_count"] == 0
    resp = await auth_client.post(
        "/api/recurring/link/refuse",
        json={"earlier_key": "OLDNAME", "later_key": "NEWNAME"},
    )
    assert resp.json()["refused_count"] == 1
    reset = await auth_client.delete("/api/recurring")
    assert reset.json()["refused_count"] == 0
