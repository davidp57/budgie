"""Envelope CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from budgie.models.category import Category, CategoryGroup
from budgie.models.envelope import Envelope, envelope_categories
from budgie.schemas.envelope import EnvelopeCreate, EnvelopeUpdate


async def get_envelopes(db: AsyncSession, user_id: int) -> list[Envelope]:
    """Return all envelopes for a user, ordered by sort_order.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of Envelope instances with categories eagerly loaded.
    """
    result = await db.execute(
        select(Envelope)
        .options(selectinload(Envelope.categories).selectinload(Category.group))
        .where(Envelope.user_id == user_id)
        .order_by(Envelope.sort_order, Envelope.id)
    )
    return list(result.scalars().all())


async def get_envelope(
    db: AsyncSession, envelope_id: int, user_id: int
) -> Envelope | None:
    """Return a single envelope by ID, scoped to the user.

    Args:
        db: Async database session.
        envelope_id: Envelope primary key.
        user_id: Owner user ID.

    Returns:
        Envelope instance with categories loaded, or None if not found.
    """
    result = await db.execute(
        select(Envelope)
        .options(selectinload(Envelope.categories).selectinload(Category.group))
        .where(Envelope.id == envelope_id, Envelope.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_envelope(
    db: AsyncSession, user_id: int, schema: EnvelopeCreate
) -> Envelope:
    """Create a new envelope and associate the given categories.

    A category can belong to at most one envelope; any existing association
    is removed before creating the new one.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        schema: Creation data (name, rollover, sort_order, category_ids).

    Returns:
        The newly created Envelope with categories loaded.
    """
    envelope = Envelope(
        user_id=user_id,
        name=schema.name,
        envelope_type=schema.envelope_type,
        period=schema.period,
        target_amount=schema.target_amount,
        stop_on_target=schema.stop_on_target,
        rollover=schema.rollover,
        sort_order=schema.sort_order,
        emoji=schema.emoji,
        color_index=schema.color_index,
    )
    db.add(envelope)
    await db.flush()
    await _set_categories(db, envelope, schema.category_ids, user_id=user_id)
    await db.commit()
    await db.refresh(envelope)
    # Reload with categories
    return await get_envelope(db, envelope.id, user_id)  # type: ignore[return-value]


async def update_envelope(
    db: AsyncSession, envelope: Envelope, schema: EnvelopeUpdate
) -> Envelope:
    """Update an existing envelope.

    Partial update: only fields provided (non-None) are changed.
    If category_ids is provided, it fully replaces the current category list.

    Args:
        db: Async database session.
        envelope: The envelope to update (already loaded).
        schema: Update data.

    Returns:
        The updated Envelope with fresh categories.
    """
    if schema.name is not None:
        envelope.name = schema.name
    if schema.envelope_type is not None:
        envelope.envelope_type = schema.envelope_type
    if schema.period is not None:
        envelope.period = schema.period
    if schema.target_amount is not None or "target_amount" in schema.model_fields_set:
        envelope.target_amount = schema.target_amount
    if schema.stop_on_target is not None:
        envelope.stop_on_target = schema.stop_on_target
    if schema.rollover is not None:
        envelope.rollover = schema.rollover
    if schema.sort_order is not None:
        envelope.sort_order = schema.sort_order
    if schema.emoji is not None:
        envelope.emoji = schema.emoji
    if schema.color_index is not None or "color_index" in schema.model_fields_set:
        envelope.color_index = schema.color_index
    if schema.category_ids is not None:
        await _set_categories(
            db, envelope, schema.category_ids, user_id=envelope.user_id
        )
    await db.commit()
    await db.refresh(envelope)
    return await get_envelope(db, envelope.id, envelope.user_id)  # type: ignore[return-value]


async def delete_envelope(db: AsyncSession, envelope: Envelope) -> None:
    """Delete an envelope (cascade deletes its allocations and category links).

    Args:
        db: Async database session.
        envelope: The envelope to delete.
    """
    await db.delete(envelope)
    await db.commit()


async def _set_categories(
    db: AsyncSession,
    envelope: Envelope,
    category_ids: list[int],
    user_id: int,
) -> None:
    """Replace all category associations for an envelope.

    Removes ``category_ids`` from any other envelope first (each category
    belongs to at most one envelope), then sets them on ``envelope``.
    Only categories owned by ``user_id`` (via their CategoryGroup) are
    accepted — foreign category IDs are silently ignored.

    Args:
        db: Async database session.
        envelope: Target envelope.
        category_ids: New set of category IDs (may be empty).
        user_id: Owner user ID (ownership check via CategoryGroup).
    """
    if not category_ids:
        # Delete all existing links for this envelope
        await db.execute(
            envelope_categories.delete().where(
                envelope_categories.c.envelope_id == envelope.id
            )
        )
        return

    # Remove these categories from any other envelope
    await db.execute(
        envelope_categories.delete().where(
            envelope_categories.c.category_id.in_(category_ids),
            envelope_categories.c.envelope_id != envelope.id,
        )
    )
    # Remove existing links for this envelope that are NOT in the new list
    await db.execute(
        envelope_categories.delete().where(
            envelope_categories.c.envelope_id == envelope.id,
            envelope_categories.c.category_id.notin_(category_ids),
        )
    )
    # Load existing links to avoid duplicate inserts
    existing_result = await db.execute(
        select(envelope_categories.c.category_id).where(
            envelope_categories.c.envelope_id == envelope.id
        )
    )
    existing_ids = {row[0] for row in existing_result.all()}

    # Verify categories exist AND belong to the user (via CategoryGroup)
    cats_result = await db.execute(
        select(Category.id)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(Category.id.in_(category_ids), CategoryGroup.user_id == user_id)
    )
    valid_ids = {row[0] for row in cats_result.all()}

    new_links = [
        {"envelope_id": envelope.id, "category_id": cid}
        for cid in category_ids
        if cid in valid_ids and cid not in existing_ids
    ]
    if new_links:
        await db.execute(envelope_categories.insert(), new_links)
