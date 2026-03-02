"""Payee CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.payee import Payee
from budgie.schemas.payee import PayeeCreate, PayeeUpdate


async def get_payees(db: AsyncSession, user_id: int) -> list[Payee]:
    """Return all payees owned by a user.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of Payee instances.
    """
    result = await db.execute(
        select(Payee).where(Payee.user_id == user_id).order_by(Payee.name)
    )
    return list(result.scalars().all())


async def get_payee(db: AsyncSession, payee_id: int, user_id: int) -> Payee | None:
    """Fetch a single payee by ID, scoped to the user.

    Args:
        db: Async database session.
        payee_id: Payee primary key.
        user_id: Owner user ID.

    Returns:
        Payee if found, None otherwise.
    """
    result = await db.execute(
        select(Payee).where(Payee.id == payee_id, Payee.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_payee(db: AsyncSession, schema: PayeeCreate, user_id: int) -> Payee:
    """Create a new payee.

    Args:
        db: Async database session.
        schema: Validated payee creation schema.
        user_id: Owner user ID.

    Returns:
        Newly created Payee instance.
    """
    payee = Payee(
        user_id=user_id,
        name=schema.name,
        auto_category_id=schema.auto_category_id,
    )
    db.add(payee)
    await db.commit()
    await db.refresh(payee)
    return payee


async def update_payee(db: AsyncSession, payee: Payee, schema: PayeeUpdate) -> Payee:
    """Partially update a payee.

    Args:
        db: Async database session.
        payee: Existing Payee instance.
        schema: Partial update schema.

    Returns:
        Updated Payee instance.
    """
    for field, value in schema.model_dump(exclude_unset=True).items():
        setattr(payee, field, value)
    await db.commit()
    await db.refresh(payee)
    return payee


async def delete_payee(db: AsyncSession, payee: Payee) -> None:
    """Delete a payee.

    Args:
        db: Async database session.
        payee: Payee instance to delete.
    """
    await db.delete(payee)
    await db.commit()
