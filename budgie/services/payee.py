"""Payee CRUD service."""

import contextlib

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.payee import Payee
from budgie.schemas.payee import PayeeCreate, PayeeUpdate
from budgie.services.crypto import InvalidKeyError, decrypt_field, encrypt_str


async def get_payees(
    db: AsyncSession,
    user_id: int,
    session_key: bytes | None = None,
) -> list[Payee]:
    """Return all payees owned by a user, with names decrypted.

    When ``session_key`` is provided, payee names are decrypted in memory
    and the list is sorted alphabetically by decrypted name.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.

    Returns:
        List of Payee instances (name decrypted when key available).
    """
    result = await db.execute(
        select(Payee).where(Payee.user_id == user_id)
    )
    payees = list(result.scalars().all())
    for payee in payees:
        if session_key is not None:
            with contextlib.suppress(InvalidKeyError, Exception):
                payee.name = decrypt_field(payee.name, session_key)
    # Sort by decrypted name (SQL ORDER BY would sort encrypted base64)
    payees.sort(key=lambda p: p.name.lower())
    return payees


async def get_payee(
    db: AsyncSession,
    payee_id: int,
    user_id: int,
    session_key: bytes | None = None,
) -> Payee | None:
    """Fetch a single payee by ID, scoped to the user.

    Args:
        db: Async database session.
        payee_id: Payee primary key.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for decryption, or None.

    Returns:
        Payee if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Payee).where(Payee.id == payee_id, Payee.user_id == user_id)
    )
    payee = result.scalar_one_or_none()
    if payee is not None and session_key is not None:
        with contextlib.suppress(InvalidKeyError, Exception):
            payee.name = decrypt_field(payee.name, session_key)
    return payee


async def create_payee(
    db: AsyncSession,
    schema: PayeeCreate,
    user_id: int,
    session_key: bytes | None = None,
) -> Payee:
    """Create a new payee.

    Args:
        db: Async database session.
        schema: Validated payee creation schema.
        user_id: Owner user ID.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        Newly created Payee instance (name decrypted for display).
    """
    encrypted_name = encrypt_str(schema.name, session_key)
    payee = Payee(
        user_id=user_id,
        name=encrypted_name if encrypted_name is not None else schema.name,
        auto_category_id=schema.auto_category_id,
    )
    db.add(payee)
    await db.commit()
    await db.refresh(payee)
    # Return with plaintext name for the API response
    payee.name = schema.name
    return payee


async def update_payee(
    db: AsyncSession,
    payee: Payee,
    schema: PayeeUpdate,
    session_key: bytes | None = None,
) -> Payee:
    """Partially update a payee.

    Args:
        db: Async database session.
        payee: Existing Payee instance.
        schema: Partial update schema.
        session_key: AES-256-GCM key for encryption, or None.

    Returns:
        Updated Payee instance (name decrypted for display).
    """
    update_data = schema.model_dump(exclude_unset=True)
    if "name" in update_data:
        plaintext_name = update_data["name"]
        update_data["name"] = encrypt_str(plaintext_name, session_key) or plaintext_name
    for field, value in update_data.items():
        setattr(payee, field, value)
    await db.commit()
    await db.refresh(payee)
    if session_key is not None:
        with contextlib.suppress(InvalidKeyError, Exception):
            payee.name = decrypt_field(payee.name, session_key)
    return payee


async def delete_payee(db: AsyncSession, payee: Payee) -> None:
    """Delete a payee.

    Args:
        db: Async database session.
        payee: Payee instance to delete.
    """
    await db.delete(payee)
    await db.commit()
