"""Free tags on recurring payments ("Phone", "Savings", "Streaming").

Tag names are encrypted at rest like every other label of the user: they are
compared, deduplicated and sorted in Python after decryption, never in SQL.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.recurring_payment import (
    RecurringPayment,
    RecurringTag,
    recurring_payment_tags,
)
from budgie.schemas.recurring import RecurringTagRead
from budgie.services.crypto import decrypt_str, encrypt_str


def _same_name(a: str, b: str) -> bool:
    """Tell whether two tag names are the same tag (case and spaces aside)."""
    return a.strip().casefold() == b.strip().casefold()


async def list_tags(
    db: AsyncSession, user_id: int, session_key: bytes | None = None
) -> list[RecurringTagRead]:
    """Return the user's tags, by name.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.

    Returns:
        The tags, names decrypted, sorted case-insensitively.
    """
    result = await db.execute(
        select(RecurringTag.id, RecurringTag.name).where(
            RecurringTag.user_id == user_id
        )
    )
    tags = [
        RecurringTagRead(id=tag_id, name=decrypt_str(name, session_key) or "")
        for tag_id, name in result.all()
    ]
    tags.sort(key=lambda t: (t.name.casefold(), t.id))
    return tags


async def create_tag(
    db: AsyncSession, name: str, user_id: int, session_key: bytes | None = None
) -> RecurringTagRead:
    """Create a tag, or return the user's tag of that name if there is one.

    Args:
        db: Async database session.
        name: Display name (already stripped by the schema).
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        The new tag, or the existing one with the same name.
    """
    name = name.strip()
    for existing in await list_tags(db, user_id, session_key):
        if _same_name(existing.name, name):
            return existing
    tag = RecurringTag(user_id=user_id, name=encrypt_str(name, session_key) or name)
    db.add(tag)
    await db.commit()
    return RecurringTagRead(id=tag.id, name=name)


async def _owned_tag(db: AsyncSession, tag_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(RecurringTag.id).where(
            RecurringTag.id == tag_id, RecurringTag.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def _owned_payment(db: AsyncSession, payment_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(RecurringPayment.id).where(
            RecurringPayment.id == payment_id, RecurringPayment.user_id == user_id
        )
    )
    return result.scalar_one_or_none() is not None


async def delete_tag(db: AsyncSession, tag_id: int, user_id: int) -> bool:
    """Delete a tag; the payments that carried it lose it.

    Args:
        db: Async database session.
        tag_id: Tag primary key.
        user_id: Owner user ID.

    Returns:
        False when the tag does not exist or belongs to another user.
    """
    if not await _owned_tag(db, tag_id, user_id):
        return False
    await db.execute(
        delete(recurring_payment_tags).where(recurring_payment_tags.c.tag_id == tag_id)
    )
    await db.execute(delete(RecurringTag).where(RecurringTag.id == tag_id))
    await db.commit()
    return True


async def _linked(db: AsyncSession, payment_id: int, tag_id: int) -> bool:
    result = await db.execute(
        select(recurring_payment_tags.c.tag_id).where(
            recurring_payment_tags.c.payment_id == payment_id,
            recurring_payment_tags.c.tag_id == tag_id,
        )
    )
    return result.first() is not None


async def tag_payment(
    db: AsyncSession, payment_id: int, tag_id: int, user_id: int
) -> bool:
    """Put a tag on a payment (nothing changes when it is already there).

    Args:
        db: Async database session.
        payment_id: Payment primary key.
        tag_id: Tag primary key.
        user_id: Owner user ID: both the payment and the tag must be theirs.

    Returns:
        False when the payment or the tag is not the user's.
    """
    if not await _owned_payment(db, payment_id, user_id):
        return False
    if not await _owned_tag(db, tag_id, user_id):
        return False
    if not await _linked(db, payment_id, tag_id):
        await db.execute(
            insert(recurring_payment_tags).values(payment_id=payment_id, tag_id=tag_id)
        )
        await db.commit()
    return True


async def untag_payment(
    db: AsyncSession, payment_id: int, tag_id: int, user_id: int
) -> bool:
    """Take a tag off a payment (nothing changes when it was not there).

    Args:
        db: Async database session.
        payment_id: Payment primary key.
        tag_id: Tag primary key.
        user_id: Owner user ID: both the payment and the tag must be theirs.

    Returns:
        False when the payment or the tag is not the user's.
    """
    if not await _owned_payment(db, payment_id, user_id):
        return False
    if not await _owned_tag(db, tag_id, user_id):
        return False
    await db.execute(
        delete(recurring_payment_tags).where(
            recurring_payment_tags.c.payment_id == payment_id,
            recurring_payment_tags.c.tag_id == tag_id,
        )
    )
    await db.commit()
    return True


async def tags_by_payment(db: AsyncSession, user_id: int) -> dict[int, list[int]]:
    """Return the tags of each of the user's payments that carries any.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        Tag IDs by payment ID, each list sorted.
    """
    result = await db.execute(
        select(recurring_payment_tags.c.payment_id, recurring_payment_tags.c.tag_id)
        .join(
            RecurringPayment,
            RecurringPayment.id == recurring_payment_tags.c.payment_id,
        )
        .where(RecurringPayment.user_id == user_id)
    )
    by_payment: dict[int, list[int]] = defaultdict(list)
    for payment_id, tag_id in result.all():
        by_payment[payment_id].append(tag_id)
    return {p: sorted(ids) for p, ids in by_payment.items()}


async def move_tags(db: AsyncSession, from_id: int, to_id: int) -> None:
    """Give a payment the tags of another one (before a merge deletes it).

    Both payments are assumed to be the same user's; nothing is committed.

    Args:
        db: Async database session.
        from_id: Payment whose tags are copied.
        to_id: Payment that receives them.
    """
    result = await db.execute(
        select(
            recurring_payment_tags.c.payment_id, recurring_payment_tags.c.tag_id
        ).where(recurring_payment_tags.c.payment_id.in_((from_id, to_id)))
    )
    rows = result.all()
    present = {tag_id for payment_id, tag_id in rows if payment_id == to_id}
    missing = sorted(
        {tag_id for payment_id, tag_id in rows if payment_id == from_id} - present
    )
    for tag_id in missing:
        await db.execute(
            insert(recurring_payment_tags).values(payment_id=to_id, tag_id=tag_id)
        )


async def delete_user_tags(db: AsyncSession, user_id: int) -> None:
    """Delete every tag of the user and its links; nothing is committed.

    Args:
        db: Async database session.
        user_id: Owner user ID.
    """
    tag_ids = select(RecurringTag.id).where(RecurringTag.user_id == user_id)
    await db.execute(
        delete(recurring_payment_tags).where(
            recurring_payment_tags.c.tag_id.in_(tag_ids)
        )
    )
    await db.execute(delete(RecurringTag).where(RecurringTag.user_id == user_id))
