"""Tests for the recurring payments service with encrypted data."""

from __future__ import annotations

import datetime
import os

from budgie.models.account import Account
from budgie.models.recurring_payment import RecurringPayment, RecurringPaymentAlias
from budgie.models.transaction import Transaction
from budgie.models.user import User
from budgie.schemas.recurring import (
    RecurringAliasCreate,
    RecurringKind,
    RecurringPaymentCreate,
)
from budgie.services import recurring as svc
from budgie.services.crypto import encrypt_str
from budgie.services.data_migration import encrypt_user_data
from budgie.services.recurring_detection import Period
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

KEY = os.urandom(32)


async def _account_with_debits(db: AsyncSession, key: bytes | None) -> int:
    user = User(username="alice", hashed_password="x")
    db.add(user)
    await db.flush()
    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    db.add(account)
    await db.flush()
    start = datetime.date.today() - datetime.timedelta(days=90)
    for i in range(4):
        day = start + datetime.timedelta(days=30 * i)
        db.add(
            Transaction(
                account_id=account.id,
                date=day,
                amount=-1399,
                memo=encrypt_str(f"CARTE {day:%d/%m/%y} STREAMFLIX CB*1", key),
                import_hash=f"h{i}",
                status="real",
            )
        )
    await db.commit()
    return user.id


def _verdict() -> RecurringPaymentCreate:
    return RecurringPaymentCreate(
        key="STREAMFLIX",
        name="Streaming",
        amount=1399,
        period=Period.MONTHLY,
        kind=RecurringKind.SUBSCRIPTION,
    )


async def test_encrypted_labels_are_read_in_clear(db_session: AsyncSession) -> None:
    user_id = await _account_with_debits(db_session, KEY)
    [candidate] = await svc.get_candidates(db_session, user_id, session_key=KEY)
    assert candidate.key == "STREAMFLIX"
    assert "STREAMFLIX" in candidate.label


async def test_name_and_key_are_encrypted_at_rest(db_session: AsyncSession) -> None:
    user_id = await _account_with_debits(db_session, KEY)
    await svc.create_payment(db_session, _verdict(), user_id, session_key=KEY)

    stored = (await db_session.execute(select(RecurringPayment))).scalar_one()
    assert "Streaming" not in stored.name
    assert "STREAMFLIX" not in stored.match_key

    overview = await svc.get_overview(db_session, user_id, session_key=KEY)
    [payment] = overview.payments
    assert payment.name == "Streaming"
    assert payment.occurrences == 4
    assert await svc.get_candidates(db_session, user_id, session_key=KEY) == []


async def test_reading_does_not_write_decrypted_values_back(
    db_session: AsyncSession,
) -> None:
    user_id = await _account_with_debits(db_session, KEY)
    await svc.create_payment(db_session, _verdict(), user_id, session_key=KEY)
    await svc.get_overview(db_session, user_id, session_key=KEY)
    await db_session.commit()
    db_session.expire_all()

    stored = (await db_session.execute(select(RecurringPayment))).scalar_one()
    assert "Streaming" not in stored.name


async def test_setting_up_encryption_encrypts_existing_payments(
    db_session: AsyncSession,
) -> None:
    user_id = await _account_with_debits(db_session, None)
    await svc.create_payment(db_session, _verdict(), user_id, session_key=None)

    await encrypt_user_data(db_session, user_id, KEY)

    stored = (await db_session.execute(select(RecurringPayment))).scalar_one()
    assert "Streaming" not in stored.name
    assert "STREAMFLIX" not in stored.match_key
    overview = await svc.get_overview(db_session, user_id, session_key=KEY)
    assert overview.payments[0].name == "Streaming"


async def test_merged_labels_are_encrypted_at_rest(db_session: AsyncSession) -> None:
    user_id = await _account_with_debits(db_session, KEY)
    first = await svc.create_payment(db_session, _verdict(), user_id, session_key=KEY)
    other = await svc.create_payment(
        db_session,
        RecurringPaymentCreate(
            key="OLDSTREAM",
            name="Old",
            amount=1399,
            period=Period.MONTHLY,
            kind=RecurringKind.SUBSCRIPTION,
        ),
        user_id,
        session_key=KEY,
    )
    # Holds the payments decrypted in memory, in the same session, during the
    # merge: the merge must not copy those in-memory plaintext labels.
    held = await svc._payments(db_session, user_id, KEY)
    assert {p.match_key for p in held} == {"STREAMFLIX", "OLDSTREAM"}
    assert await svc.merge_payments(db_session, first, other, user_id, session_key=KEY)
    del held
    await svc.add_alias(
        db_session,
        first,
        RecurringAliasCreate(key="THIRDNAME", amount=1399),
        user_id,
        session_key=KEY,
    )
    db_session.expire_all()

    stored = (await db_session.execute(select(RecurringPaymentAlias))).scalars().all()
    assert len(stored) == 2
    for alias in stored:
        assert "STREAM" not in alias.match_key
        assert "THIRDNAME" not in alias.match_key
    overview = await svc.get_overview(db_session, user_id, session_key=KEY)
    [payment] = overview.payments
    assert sorted(a.key for a in payment.aliases) == ["OLDSTREAM", "THIRDNAME"]
