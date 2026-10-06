"""Ownership checks for foreign-key references supplied by API clients.

Clients send raw IDs (``category_id``, ``envelope_id``, ``payee_id``) when
creating or updating rules, payees and transactions.  Those IDs must point to
objects owned by the same user, otherwise one account could attach its data
to — and later read back the names of — another account's objects.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.category import Category, CategoryGroup
from budgie.models.envelope import Envelope
from budgie.models.payee import Payee


class ForeignReferenceError(LookupError):
    """Raised when a referenced object does not exist or belongs to another user."""


async def ensure_references_owned(
    db: AsyncSession,
    user_id: int,
    *,
    category_id: int | None = None,
    envelope_id: int | None = None,
    payee_id: int | None = None,
) -> None:
    """Verify that every non-None reference belongs to *user_id*.

    Args:
        db: Async database session.
        user_id: Authenticated user ID.
        category_id: Optional category reference to check.
        envelope_id: Optional envelope reference to check.
        payee_id: Optional payee reference to check.

    Raises:
        ForeignReferenceError: If a reference is unknown or owned by another
            user.  Both cases share the same message so that the response
            does not reveal whether the ID exists.
    """
    if category_id is not None:
        found = await db.scalar(
            select(Category.id)
            .join(CategoryGroup, Category.group_id == CategoryGroup.id)
            .where(Category.id == category_id, CategoryGroup.user_id == user_id)
        )
        if found is None:
            raise ForeignReferenceError("Category not found")
    if envelope_id is not None:
        found = await db.scalar(
            select(Envelope.id).where(
                Envelope.id == envelope_id, Envelope.user_id == user_id
            )
        )
        if found is None:
            raise ForeignReferenceError("Envelope not found")
    if payee_id is not None:
        found = await db.scalar(
            select(Payee.id).where(Payee.id == payee_id, Payee.user_id == user_id)
        )
        if found is None:
            raise ForeignReferenceError("Payee not found")
