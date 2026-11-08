"""Recurring payments service: candidates, classification and tracking.

Bank labels are encrypted at rest, so every grouping happens in Python after
decryption (see :mod:`budgie.services.recurring_detection` for the logic).
"""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from budgie.models.account import Account
from budgie.models.recurring_payment import RecurringPayment, RecurringPaymentAlias
from budgie.models.transaction import Transaction
from budgie.schemas.recurring import (
    RecurringAliasCreate,
    RecurringAliasRead,
    RecurringCandidateRead,
    RecurringKind,
    RecurringOverview,
    RecurringPaymentCreate,
    RecurringPaymentRead,
    RecurringPaymentUpdate,
)
from budgie.services.crypto import decrypt_str, encrypt_str
from budgie.services.ownership import ensure_references_owned
from budgie.services.recurring_detection import (
    BankDebit,
    PaymentStatus,
    PaymentTrack,
    Period,
    TrackedPayment,
    amount_matches,
    debits_after_cancellation,
    detect_series,
    monthly_cost,
    normalize_label,
    payment_status,
    track_payments,
)

#: Months in a year, for the yearly total.
MONTHS_PER_YEAR = 12


async def _bank_debits(
    db: AsyncSession, user_id: int, session_key: bytes | None
) -> list[BankDebit]:
    """Load the user's imported bank debits, labels decrypted.

    Only imported transactions count: a manual expense reconciled with a bank
    line would otherwise be counted twice.
    """
    result = await db.execute(
        select(Transaction.date, Transaction.amount, Transaction.memo)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Transaction.import_hash.is_not(None),
            Transaction.amount < 0,
            Transaction.status != "planned",
        )
    )
    debits: list[BankDebit] = []
    for date, amount, memo in result.all():
        label = decrypt_str(memo, session_key) or ""
        if label:
            debits.append(BankDebit(date=date, amount=-amount, label=label))
    return debits


async def _payments(
    db: AsyncSession, user_id: int, session_key: bytes | None
) -> list[RecurringPayment]:
    """Load the user's classified payments, name and key decrypted in memory."""
    result = await db.execute(
        select(RecurringPayment)
        .where(RecurringPayment.user_id == user_id)
        .options(selectinload(RecurringPayment.aliases))
        .order_by(RecurringPayment.id)
        # Reload rows already in the session: their decrypted values and alias
        # lists may predate a change made earlier in the same session.
        .execution_options(populate_existing=True)
    )
    payments = list(result.scalars().all())
    for payment in payments:
        # Committed values: the decrypted text is never flushed back.
        set_committed_value(
            payment, "name", decrypt_str(payment.name, session_key) or ""
        )
        set_committed_value(
            payment, "match_key", decrypt_str(payment.match_key, session_key) or ""
        )
        for alias in payment.aliases:
            set_committed_value(
                alias, "match_key", decrypt_str(alias.match_key, session_key) or ""
            )
    return payments


def _tracked(payments: list[RecurringPayment]) -> list[TrackedPayment]:
    """Every label of every payment: the main one, then the merged ones."""
    labels: list[TrackedPayment] = []
    for p in payments:
        period = Period(p.period)
        labels.append(
            TrackedPayment(id=p.id, key=p.match_key, amount=p.amount, period=period)
        )
        labels.extend(
            TrackedPayment(
                id=p.id, key=a.match_key, amount=a.amount, period=period, alias_id=a.id
            )
            for a in p.aliases
        )
    return labels


async def get_candidates(
    db: AsyncSession, user_id: int, session_key: bytes | None = None
) -> list[RecurringCandidateRead]:
    """Find the recurring debits the user has not classified yet.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.

    Returns:
        Candidates, most expensive per month first.
    """
    debits = await _bank_debits(db, user_id, session_key)
    payments = await _payments(db, user_id, session_key)
    _, unattributed = track_payments(debits, _tracked(payments))
    return [
        RecurringCandidateRead(
            key=s.key,
            label=s.label,
            amount=s.amount,
            period=s.period,
            monthly_cost=s.monthly_cost,
            occurrences=s.occurrences,
            first_date=s.first_date,
            last_date=s.last_date,
        )
        for s in detect_series(unattributed)
    ]


def _read(
    payment: RecurringPayment, track: PaymentTrack, today: datetime.date
) -> RecurringPaymentRead:
    period = Period(payment.period)
    return RecurringPaymentRead(
        id=payment.id,
        key=payment.match_key,
        name=payment.name,
        kind=RecurringKind(payment.kind),
        period=period,
        amount=payment.amount,
        current_amount=track.current_amount,
        monthly_cost=monthly_cost(track.current_amount, period),
        category_id=payment.category_id,
        cancelled_at=payment.cancelled_at,
        last_date=track.last_date,
        occurrences=len(track.dates),
        status=payment_status(track, period, payment.cancelled_at, today),
        price_changed=not amount_matches(
            track.current_amount,
            track.last_reference
            if track.last_reference is not None
            else payment.amount,
        ),
        debits_after_cancellation=debits_after_cancellation(
            track, payment.cancelled_at
        ),
        aliases=[
            RecurringAliasRead(id=a.id, key=a.match_key, amount=a.amount)
            for a in payment.aliases
        ],
    )


def _needs_attention(payment: RecurringPaymentRead) -> bool:
    """A subscription to look at: stopped, debited after cancellation, new price.

    A price change on a cancelled subscription no longer matters.
    """
    if payment.kind is not RecurringKind.SUBSCRIPTION:
        return False
    if payment.status is PaymentStatus.CANCELLED:
        return bool(payment.debits_after_cancellation)
    return payment.status is PaymentStatus.PROBABLY_ENDED or payment.price_changed


async def get_overview(
    db: AsyncSession,
    user_id: int,
    session_key: bytes | None = None,
    today: datetime.date | None = None,
) -> RecurringOverview:
    """Return every classified payment and the cost of the subscriptions.

    The total counts active subscriptions only: a cancelled or probably ended
    one no longer costs anything.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.
        today: Reference date for the statuses (defaults to today).

    Returns:
        The overview.
    """
    today = today or datetime.date.today()
    debits = await _bank_debits(db, user_id, session_key)
    payments = await _payments(db, user_id, session_key)
    tracks, _ = track_payments(debits, _tracked(payments))
    reads = [_read(p, tracks[p.id], today) for p in payments]
    reads.sort(key=lambda r: (-r.monthly_cost, r.name.lower()))
    monthly_total = sum(
        r.monthly_cost
        for r in reads
        if r.kind is RecurringKind.SUBSCRIPTION and r.status is PaymentStatus.ACTIVE
    )
    return RecurringOverview(
        payments=reads,
        monthly_total=monthly_total,
        yearly_total=monthly_total * MONTHS_PER_YEAR,
        attention_count=sum(_needs_attention(r) for r in reads),
    )


async def _owned(
    db: AsyncSession, payment_id: int, user_id: int
) -> RecurringPayment | None:
    result = await db.execute(
        select(RecurringPayment).where(
            RecurringPayment.id == payment_id, RecurringPayment.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_payment(
    db: AsyncSession,
    schema: RecurringPaymentCreate,
    user_id: int,
    session_key: bytes | None = None,
) -> int:
    """Record the user's verdict on a candidate.

    Args:
        db: Async database session.
        schema: The verdict.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        ID of the new payment.
    """
    payment = RecurringPayment(
        user_id=user_id,
        name=encrypt_str(schema.name, session_key) or schema.name,
        match_key=encrypt_str(normalize_label(schema.key), session_key)
        or normalize_label(schema.key),
        amount=schema.amount,
        period=schema.period.value,
        kind=schema.kind.value,
    )
    db.add(payment)
    await db.commit()
    return payment.id


async def update_payment(
    db: AsyncSession,
    payment_id: int,
    schema: RecurringPaymentUpdate,
    user_id: int,
    session_key: bytes | None = None,
) -> bool:
    """Change a classified payment.

    Args:
        db: Async database session.
        payment_id: Payment primary key.
        schema: Fields to change (only those sent).
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        False when the payment does not exist or belongs to another user.

    Raises:
        ForeignReferenceError: If the category belongs to another user.
    """
    payment = await _owned(db, payment_id, user_id)
    if payment is None:
        return False
    sent = schema.model_fields_set
    if "category_id" in sent and schema.category_id is not None:
        await ensure_references_owned(db, user_id, category_id=schema.category_id)
    if "name" in sent and schema.name is not None:
        payment.name = encrypt_str(schema.name, session_key) or schema.name
    if "kind" in sent and schema.kind is not None:
        payment.kind = schema.kind.value
    if "amount" in sent and schema.amount is not None:
        payment.amount = schema.amount
    if "category_id" in sent:
        payment.category_id = schema.category_id
    if "cancelled_at" in sent:
        payment.cancelled_at = schema.cancelled_at
    await db.commit()
    return True


async def delete_payment(db: AsyncSession, payment_id: int, user_id: int) -> bool:
    """Forget a classification: its debits become a candidate again.

    Args:
        db: Async database session.
        payment_id: Payment primary key.
        user_id: Owner user ID.

    Returns:
        False when the payment does not exist or belongs to another user.
    """
    payment = await _owned(db, payment_id, user_id)
    if payment is None:
        return False
    await db.delete(payment)
    await db.commit()
    return True


def _reencrypt(value: str, session_key: bytes | None) -> str:
    """Return a stored label encrypted with the session key.

    Works whether the in-memory value is still the ciphertext or was
    decrypted earlier in the same session.
    """
    plain = decrypt_str(value, session_key) or value
    return encrypt_str(plain, session_key) or plain


async def add_alias(
    db: AsyncSession,
    payment_id: int,
    schema: RecurringAliasCreate,
    user_id: int,
    session_key: bytes | None = None,
) -> bool:
    """Merge a candidate's label into a classified payment.

    Args:
        db: Async database session.
        payment_id: Payment the label is merged into.
        schema: Label and amount of the candidate.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        False when the payment does not exist or belongs to another user.
    """
    payment = await _owned(db, payment_id, user_id)
    if payment is None:
        return False
    key = normalize_label(schema.key)
    if not await _carries_label(db, payment, key, schema.amount, session_key):
        db.add(
            RecurringPaymentAlias(
                payment_id=payment.id,
                match_key=encrypt_str(key, session_key) or key,
                amount=schema.amount,
            )
        )
    await db.commit()
    return True


async def _carries_label(
    db: AsyncSession,
    payment: RecurringPayment,
    key: str,
    amount: int,
    session_key: bytes | None,
) -> bool:
    """Tell whether a payment already carries a label at about this amount."""
    aliases = (
        (
            await db.execute(
                select(RecurringPaymentAlias).where(
                    RecurringPaymentAlias.payment_id == payment.id
                )
            )
        )
        .scalars()
        .all()
    )
    labels = [(payment.match_key, payment.amount)]
    labels += [(a.match_key, a.amount) for a in aliases]
    return any(
        (decrypt_str(stored, session_key) or stored) == key
        and amount_matches(amount, reference)
        for stored, reference in labels
    )


async def merge_payments(
    db: AsyncSession,
    payment_id: int,
    other_id: int,
    user_id: int,
    session_key: bytes | None = None,
) -> bool:
    """Merge another classified payment into this one.

    The payment keeps its name, kind, category and cancellation; the main
    label and the merged labels of the other become its own, and the other
    payment is deleted.

    Args:
        db: Async database session.
        payment_id: Payment that absorbs the other.
        other_id: Payment to absorb.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        False when either payment does not exist, belongs to another user, or
        both are the same payment.
    """
    if payment_id == other_id:
        return False
    target = await _owned(db, payment_id, user_id)
    other = await _owned(db, other_id, user_id)
    if target is None or other is None:
        return False
    other_aliases = (
        (
            await db.execute(
                select(RecurringPaymentAlias).where(
                    RecurringPaymentAlias.payment_id == other.id
                )
            )
        )
        .scalars()
        .all()
    )
    labels = [(other.match_key, other.amount)]
    labels += [(a.match_key, a.amount) for a in other_aliases]
    for match_key, amount in labels:
        key = decrypt_str(match_key, session_key) or match_key
        if await _carries_label(db, target, key, amount, session_key):
            continue
        db.add(
            RecurringPaymentAlias(
                payment_id=target.id,
                match_key=_reencrypt(match_key, session_key),
                amount=amount,
            )
        )
        await db.flush()
    await db.delete(other)
    await db.commit()
    return True


async def remove_alias(
    db: AsyncSession, payment_id: int, alias_id: int, user_id: int
) -> bool:
    """Detach a merged label: its debits become a candidate again.

    Args:
        db: Async database session.
        payment_id: Payment the label is merged into.
        alias_id: Merged label to detach.
        user_id: Owner user ID.

    Returns:
        False when the label does not exist, belongs to another payment, or
        the payment belongs to another user.
    """
    result = await db.execute(
        select(RecurringPaymentAlias)
        .join(RecurringPayment, RecurringPaymentAlias.payment_id == RecurringPayment.id)
        .where(
            RecurringPaymentAlias.id == alias_id,
            RecurringPaymentAlias.payment_id == payment_id,
            RecurringPayment.user_id == user_id,
        )
    )
    alias = result.scalar_one_or_none()
    if alias is None:
        return False
    await db.delete(alias)
    await db.commit()
    return True


async def accept_price(
    db: AsyncSession,
    payment_id: int,
    user_id: int,
    session_key: bytes | None = None,
) -> bool:
    """Take the latest debited amount as the new reference price.

    The reference changed is the one of the label that billed the most recent
    debit (the main label or a merged one), so that the other labels keep
    their own history.

    Args:
        db: Async database session.
        payment_id: Payment primary key.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.

    Returns:
        False when the payment does not exist or belongs to another user.
    """
    if await _owned(db, payment_id, user_id) is None:
        return False
    debits = await _bank_debits(db, user_id, session_key)
    payments = await _payments(db, user_id, session_key)
    tracks, _ = track_payments(debits, _tracked(payments))
    track = tracks[payment_id]
    if track.last_reference is None:
        return True
    payment = next(p for p in payments if p.id == payment_id)
    if track.last_alias_id is None:
        payment.amount = track.current_amount
    else:
        alias = next(a for a in payment.aliases if a.id == track.last_alias_id)
        alias.amount = track.current_amount
    await db.commit()
    return True
