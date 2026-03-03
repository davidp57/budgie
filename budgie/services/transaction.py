"""Transaction CRUD service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.transaction import Transaction
from budgie.schemas.transaction import TransactionCreate, TransactionUpdate


async def get_transactions(
    db: AsyncSession,
    user_id: int,
    account_id: int | None = None,
    is_virtual: bool | None = None,
    month: str | None = None,
    category_ids: list[int] | None = None,
) -> list[Transaction]:
    """Return transactions for a user, optionally filtered by account or type.

    Args:
        db: Async database session.
        user_id: Owner user ID (for authorization via account ownership).
        account_id: If provided, filter to this account only.
        is_virtual: If provided, filter to virtual or real transactions only.
        month: If provided, filter to transactions in this YYYY-MM month only.
        category_ids: If provided, filter to transactions whose category_id is
            in this list. Pass an empty list to return uncategorised transactions
            only.

    Returns:
        List of Transaction instances ordered by date descending.
    """
    query = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id)
        .order_by(Transaction.date.desc())
    )
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if is_virtual is not None:
        query = query.where(Transaction.is_virtual == is_virtual)
    if month is not None:
        query = query.where(func.strftime("%Y-%m", Transaction.date) == month)
    if category_ids is not None:
        query = query.where(Transaction.category_id.in_(category_ids))

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_virtual_unlinked(
    db: AsyncSession,
    user_id: int,
) -> list[Transaction]:
    """Return all unlinked (pending) virtual transactions for a user.

    These are virtual transactions that have not yet been matched to a
    real imported transaction (virtual_linked_id is None and not
    reconciled).

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of pending virtual Transaction instances ordered by date.
    """
    query = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Transaction.is_virtual == True,  # noqa: E712
            Transaction.cleared != "reconciled",
        )
        .order_by(Transaction.date.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def link_virtual(
    db: AsyncSession,
    real_txn: Transaction,
    virtual_id: int,
    user_id: int,
) -> Transaction:
    """Link a real transaction to a virtual one, marking the virtual as realized.

    Sets ``virtual_linked_id`` on the real transaction and marks the
    virtual transaction as ``cleared='reconciled'``.

    Args:
        db: Async database session.
        real_txn: The real (imported) transaction to update.
        virtual_id: ID of the virtual transaction to mark as realized.
        user_id: Owner user ID (for authorization).

    Returns:
        Updated real Transaction instance.

    Raises:
        ValueError: If the virtual transaction is not found or not owned by user.
    """
    virtual_txn = await get_transaction(db, virtual_id, user_id)
    if virtual_txn is None or not virtual_txn.is_virtual:
        raise ValueError(f"Virtual transaction {virtual_id} not found")

    real_txn.virtual_linked_id = virtual_id
    virtual_txn.cleared = "reconciled"
    await db.commit()
    await db.refresh(real_txn)
    return real_txn


async def get_transaction(
    db: AsyncSession, transaction_id: int, user_id: int
) -> Transaction | None:
    """Fetch a single transaction by ID, scoped to the user.

    Args:
        db: Async database session.
        transaction_id: Transaction primary key.
        user_id: Owner user ID.

    Returns:
        Transaction if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == transaction_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_transaction(
    db: AsyncSession, schema: TransactionCreate
) -> Transaction:
    """Create a new transaction.

    Args:
        db: Async database session.
        schema: Validated transaction creation schema.

    Returns:
        Newly created Transaction instance.
    """
    txn = Transaction(**schema.model_dump())
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return txn


async def update_transaction(
    db: AsyncSession, txn: Transaction, schema: TransactionUpdate
) -> Transaction:
    """Partially update a transaction.

    Args:
        db: Async database session.
        txn: Existing Transaction instance.
        schema: Partial update schema.

    Returns:
        Updated Transaction instance.
    """
    for field, value in schema.model_dump(exclude_unset=True).items():
        setattr(txn, field, value)
    await db.commit()
    await db.refresh(txn)
    return txn


async def delete_transaction(db: AsyncSession, txn: Transaction) -> None:
    """Delete a transaction.

    Args:
        db: Async database session.
        txn: Transaction instance to delete.
    """
    await db.delete(txn)
    await db.commit()
