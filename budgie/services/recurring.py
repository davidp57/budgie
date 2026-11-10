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
from budgie.models.recurring_payment import (
    RecurringLinkRefusal,
    RecurringPayment,
    RecurringPaymentAlias,
)
from budgie.models.transaction import Transaction
from budgie.schemas.recurring import (
    PriceSegmentRead,
    RecurringAliasCreate,
    RecurringAliasRead,
    RecurringBoard,
    RecurringCandidateRead,
    RecurringDebitRead,
    RecurringKind,
    RecurringLine,
    RecurringLineRef,
    RecurringLink,
    RecurringLinkSuggestion,
    RecurringOverview,
    RecurringPaymentCreate,
    RecurringPaymentRead,
    RecurringPaymentUpdate,
    RecurringSummary,
    RecurringSummaryItem,
)
from budgie.services.crypto import decrypt_str, encrypt_str
from budgie.services.ownership import ensure_references_owned
from budgie.services.recurring_detection import (
    BankDebit,
    LineSpan,
    PaymentStatus,
    PaymentTrack,
    Period,
    SeriesChain,
    TrackedPayment,
    amount_matches,
    chain_series,
    debits_after_cancellation,
    detect_series,
    is_running,
    monthly_cost,
    normalize_label,
    payment_status,
    price_segments,
    suggest_links,
    track_payments,
)
from budgie.services.recurring_tags import (
    delete_user_tags,
    list_tags,
    move_tags,
    tags_by_payment,
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
        cancelled_at=schema.cancelled_at,
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
    label, the merged labels and the tags of the other become its own, and
    the other payment is deleted.

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
    await move_tags(db, other.id, target.id)
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


#: An unclassified line costing this much per month is probably not a
#: subscription (taxes, savings, rent, insurance), in centimes.
LIKELY_OTHER_MONTHLY_COST = 10_000

#: Label prefixes of transfers, which are never subscriptions.
_TRANSFER_PREFIXES = ("VIR ", "VIREMENT")


def display_name(key: str) -> str:
    """Readable default name of a normalized key ("STREAM FLIX" -> "Stream Flix")."""
    return " ".join(w.capitalize() for w in key.split())


def _likely_other(chain: SeriesChain) -> bool:
    label = chain.latest.label.strip().upper()
    return chain.latest.monthly_cost >= LIKELY_OTHER_MONTHLY_COST or label.startswith(
        _TRANSFER_PREFIXES
    )


def _segments(dates: list[datetime.date], amounts: list[int]) -> list[PriceSegmentRead]:
    return [
        PriceSegmentRead(start=s.start, end=s.end, amount=s.amount, count=s.count)
        for s in price_segments(list(zip(dates, amounts, strict=True)))
    ]


def _payment_line(
    read: RecurringPaymentRead, track: PaymentTrack, today: datetime.date
) -> RecurringLine:
    return RecurringLine(
        id=f"p{read.id}",
        ref=RecurringLineRef(payment_id=read.id),
        payment=read,
        name=read.name,
        key=read.key,
        label=None,
        period=read.period,
        amount=read.current_amount,
        monthly_cost=read.monthly_cost,
        first_date=track.dates[0] if track.dates else None,
        last_date=read.last_date,
        running=read.status is PaymentStatus.ACTIVE
        and read.last_date is not None
        and is_running(read.last_date, read.period, today),
        likely_other=False,
        segments=_segments(track.dates, track.amounts),
    )


def _chain_line(chain: SeriesChain, today: datetime.date) -> RecurringLine:
    hits = chain.hits
    return RecurringLine(
        id=f"s{chain.key}|{chain.amount}|{chain.first_date.isoformat()}",
        ref=RecurringLineRef(key=chain.key, amount=chain.amount, period=chain.period),
        payment=None,
        name=display_name(chain.key),
        key=chain.key,
        label=chain.latest.label,
        period=chain.period,
        amount=chain.amount,
        monthly_cost=chain.latest.monthly_cost,
        first_date=chain.first_date,
        last_date=chain.last_date,
        running=is_running(chain.last_date, chain.period, today),
        likely_other=_likely_other(chain),
        segments=_segments([h.date for h in hits], [h.amount for h in hits]),
    )


def _counts_in_total(line: RecurringLine) -> bool:
    if not line.running:
        return False
    if line.payment is None:
        return not line.likely_other
    return line.payment.kind is RecurringKind.SUBSCRIPTION


async def get_board(
    db: AsyncSession,
    user_id: int,
    session_key: bytes | None = None,
    today: datetime.date | None = None,
) -> RecurringBoard:
    """Return every service line, classified or not, and what runs now.

    A line not classified yet is a chain of detected series of one label;
    the total counts it as a subscription unless it is probably something
    else, so that the answer comes before any classification.  "Running" and
    the statuses are judged as of the most recent imported debit: the board
    describes the situation of the last statement imported.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.
        today: Date used when no debit was imported (defaults to today).

    Returns:
        The board.
    """
    debits = await _bank_debits(db, user_id, session_key)
    as_of = max((d.date for d in debits), default=today or datetime.date.today())
    today = as_of
    payments = await _payments(db, user_id, session_key)
    tracks, unattributed = track_payments(debits, _tracked(payments))

    lines = [
        _payment_line(_read(p, tracks[p.id], today), tracks[p.id], today)
        for p in payments
    ]
    lines += [_chain_line(c, today) for c in chain_series(detect_series(unattributed))]
    lines.sort(key=lambda line: (-line.monthly_cost, line.name.lower()))

    in_total = [line for line in lines if _counts_in_total(line)]
    monthly_total = sum(line.monthly_cost for line in in_total)
    visible = [
        line
        for line in lines
        if line.segments
        and (line.payment is None or line.payment.kind is not RecurringKind.DISMISSED)
    ]
    spans = [
        LineSpan(
            id=line.id,
            key=line.key,
            first_date=line.segments[0].start,
            last_date=line.segments[-1].end,
            first_amount=line.segments[0].amount,
            last_amount=line.segments[-1].amount,
            period=line.period,
        )
        for line in visible
    ]
    refused = await _refusals(db, user_id, session_key)
    suggestions = suggest_links(spans, refused)
    return RecurringBoard(
        as_of=as_of,
        lines=lines,
        monthly_total=monthly_total,
        yearly_total=monthly_total * MONTHS_PER_YEAR,
        refused_count=len(refused),
        estimated_count=sum(line.payment is None for line in in_total),
        attention_count=sum(
            line.payment is not None and _needs_attention(line.payment)
            for line in lines
        ),
        suggestions=[
            RecurringLinkSuggestion(earlier_id=a, later_id=b) for a, b in suggestions
        ],
    )


#: Kinds of payment the user kept: the presentation lists them.
_KEPT_KINDS = (RecurringKind.SUBSCRIPTION, RecurringKind.OTHER)


def _summary_item(
    read: RecurringPaymentRead, track: PaymentTrack, tag_ids: list[int]
) -> RecurringSummaryItem:
    return RecurringSummaryItem(
        id=read.id,
        name=read.name,
        kind=read.kind,
        period=read.period,
        amount=read.current_amount,
        monthly_cost=read.monthly_cost,
        category_id=read.category_id,
        first_date=track.dates[0],
        last_date=track.dates[-1],
        occurrences=len(track.dates),
        tag_ids=tag_ids,
        debits=[
            RecurringDebitRead(date=d, amount=a)
            for d, a in reversed(list(zip(track.dates, track.amounts, strict=True)))
        ],
        segments=_segments(track.dates, track.amounts),
    )


async def get_summary(
    db: AsyncSession,
    user_id: int,
    session_key: bytes | None = None,
    today: datetime.date | None = None,
) -> RecurringSummary:
    """Return the recurring payments the user kept that run now, with history.

    Kept means classified as a subscription or as another recurring payment;
    running means not cancelled and debited within the last one and a half
    periods, judged as of the most recent imported debit (like the board).

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.
        today: Date used when no debit was imported (defaults to today).

    Returns:
        The presentation.
    """
    debits = await _bank_debits(db, user_id, session_key)
    as_of = max((d.date for d in debits), default=today or datetime.date.today())
    payments = await _payments(db, user_id, session_key)
    tracks, unattributed = track_payments(debits, _tracked(payments))
    tag_ids = await tags_by_payment(db, user_id)

    reads = [(_read(p, tracks[p.id], as_of), tracks[p.id]) for p in payments]
    items = [
        _summary_item(read, track, tag_ids.get(read.id, []))
        for read, track in reads
        if read.kind in _KEPT_KINDS
        and read.status is PaymentStatus.ACTIVE
        and track.dates
    ]
    items.sort(key=lambda i: (-i.monthly_cost, i.name.lower()))
    subscriptions = sum(
        i.monthly_cost for i in items if i.kind is RecurringKind.SUBSCRIPTION
    )
    total = sum(i.monthly_cost for i in items)
    to_confirm = sum(
        is_running(c.last_date, c.period, as_of) and not _likely_other(c)
        for c in chain_series(detect_series(unattributed))
    )
    return RecurringSummary(
        as_of=as_of,
        items=items,
        tags=await list_tags(db, user_id, session_key),
        subscriptions_monthly=subscriptions,
        subscriptions_yearly=subscriptions * MONTHS_PER_YEAR,
        monthly_total=total,
        yearly_total=total * MONTHS_PER_YEAR,
        to_confirm_count=to_confirm,
        attention_count=sum(_needs_attention(read) for read, _ in reads),
    )


async def _chain_of(
    db: AsyncSession,
    ref: RecurringLineRef,
    user_id: int,
    session_key: bytes | None,
) -> SeriesChain | None:
    """Find the detected line a reference points at, as the board shows it."""
    if ref.key is None or ref.amount is None or ref.period is None:
        return None
    key = normalize_label(ref.key)
    debits = await _bank_debits(db, user_id, session_key)
    payments = await _payments(db, user_id, session_key)
    _, unattributed = track_payments(debits, _tracked(payments))
    for chain in chain_series(detect_series(unattributed)):
        if (
            chain.key == key
            and chain.amount == ref.amount
            and chain.period == ref.period
        ):
            return chain
    return None


async def _attach_chain(
    db: AsyncSession,
    payment_id: int,
    chain: SeriesChain,
    user_id: int,
    session_key: bytes | None,
    *,
    include_latest: bool,
) -> None:
    """Merge every price of a detected line into a payment.

    Each price becomes a merged label, so that the tracking finds every debit
    of the line, even across a missing month or a change of rhythm.
    """
    series = chain.series if include_latest else chain.series[:-1]
    for s in series:
        await add_alias(
            db,
            payment_id,
            RecurringAliasCreate(key=chain.key, amount=s.amount),
            user_id,
            session_key=session_key,
        )


async def classify_line(
    db: AsyncSession,
    schema: RecurringPaymentCreate,
    user_id: int,
    session_key: bytes | None = None,
) -> int:
    """Classify a detected line, with every price it was billed at.

    The payment takes the line's current price; its earlier prices become
    merged labels, so that the whole history stays on the one line.

    Args:
        db: Async database session.
        schema: The verdict on the line (its current price and rhythm).
        user_id: Owner user ID.
        session_key: AES-256-GCM key, or None.

    Returns:
        ID of the new payment.
    """
    chain = await _chain_of(
        db,
        RecurringLineRef(key=schema.key, amount=schema.amount, period=schema.period),
        user_id,
        session_key,
    )
    payment_id = await create_payment(db, schema, user_id, session_key=session_key)
    if chain is not None:
        await _attach_chain(
            db, payment_id, chain, user_id, session_key, include_latest=False
        )
    return payment_id


async def _payment_for(
    db: AsyncSession,
    ref: RecurringLineRef,
    user_id: int,
    session_key: bytes | None,
) -> int | None:
    """Return the payment of a line, classifying it as a subscription if needed."""
    if ref.payment_id is not None:
        owned = await _owned(db, ref.payment_id, user_id)
        return owned.id if owned is not None else None
    if ref.key is None or ref.amount is None or ref.period is None:
        return None
    return await classify_line(
        db,
        RecurringPaymentCreate(
            key=ref.key,
            name=display_name(normalize_label(ref.key)),
            amount=ref.amount,
            period=ref.period,
            kind=RecurringKind.SUBSCRIPTION,
        ),
        user_id,
        session_key=session_key,
    )


async def link_lines(
    db: AsyncSession,
    link: RecurringLink,
    user_id: int,
    session_key: bytes | None = None,
) -> bool:
    """Join two lines that are one service under two labels.

    A classified line keeps its classification (name, kind, category,
    cancellation): when only the earlier line is classified, the later
    line's labels are merged into it.  Otherwise the later line absorbs the
    earlier one, being classified as a subscription first when it was not.
    A detected line brings every price it was billed at.

    Args:
        db: Async database session.
        link: The two lines.
        user_id: Owner user ID.
        session_key: AES-256-GCM key, or None.

    Returns:
        False when a referenced payment is not the user's, a reference is
        incomplete or matches no line, or both lines are the same payment.
    """
    earlier, later = link.earlier, link.later
    if earlier.payment_id is not None and earlier.payment_id == later.payment_id:
        return False

    if earlier.payment_id is not None and later.payment_id is None:
        if await _owned(db, earlier.payment_id, user_id) is None:
            return False
        later_chain = await _chain_of(db, later, user_id, session_key)
        if later_chain is None:
            return False
        await _attach_chain(
            db,
            earlier.payment_id,
            later_chain,
            user_id,
            session_key,
            include_latest=True,
        )
        return True

    earlier_chain: SeriesChain | None = None
    if earlier.payment_id is not None:
        if await _owned(db, earlier.payment_id, user_id) is None:
            return False
    else:
        earlier_chain = await _chain_of(db, earlier, user_id, session_key)
        if earlier_chain is None:
            return False
    target = await _payment_for(db, later, user_id, session_key)
    if target is None:
        return False
    if earlier_chain is not None:
        await _attach_chain(
            db, target, earlier_chain, user_id, session_key, include_latest=True
        )
        return True
    if earlier.payment_id is None:
        return False
    return await merge_payments(
        db, target, earlier.payment_id, user_id, session_key=session_key
    )


async def reset_payments(db: AsyncSession, user_id: int) -> int:
    """Forget every classification of the user; imported transactions stay.

    Refused link suggestions and tags are classifications too: they are
    forgotten.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        Number of classified payments removed (their merged labels go too).
    """
    result = await db.execute(
        select(RecurringPayment).where(RecurringPayment.user_id == user_id)
    )
    payments = list(result.scalars().all())
    for payment in payments:
        await db.delete(payment)
    refusals = await db.execute(
        select(RecurringLinkRefusal).where(RecurringLinkRefusal.user_id == user_id)
    )
    for refusal in refusals.scalars().all():
        await db.delete(refusal)
    await delete_user_tags(db, user_id)
    await db.commit()
    return len(payments)


async def _refusals(
    db: AsyncSession, user_id: int, session_key: bytes | None
) -> set[tuple[str, str]]:
    """The link suggestions the user said no to, as (earlier key, later key)."""
    result = await db.execute(
        select(RecurringLinkRefusal.earlier_key, RecurringLinkRefusal.later_key).where(
            RecurringLinkRefusal.user_id == user_id
        )
    )
    return {
        (
            decrypt_str(earlier, session_key) or earlier,
            decrypt_str(later, session_key) or later,
        )
        for earlier, later in result.all()
    }


async def refuse_link(
    db: AsyncSession,
    earlier_key: str,
    later_key: str,
    user_id: int,
    session_key: bytes | None = None,
) -> None:
    """Say no to a link suggestion, so that it is not made again.

    Args:
        db: Async database session.
        earlier_key: Label of the line that stopped.
        later_key: Label of the line that followed.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.
    """
    earlier = normalize_label(earlier_key)
    later = normalize_label(later_key)
    if (earlier, later) in await _refusals(db, user_id, session_key):
        return
    db.add(
        RecurringLinkRefusal(
            user_id=user_id,
            earlier_key=encrypt_str(earlier, session_key) or earlier,
            later_key=encrypt_str(later, session_key) or later,
        )
    )
    await db.commit()
