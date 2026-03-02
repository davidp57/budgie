"""Transaction CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.transaction import Transaction
from budgie.schemas.transaction import TransactionCreate, TransactionUpdate


async def get_transactions(
    db: AsyncSession,
    user_id: int,
    account_id: int | None = None,
) -> list[Transaction]:
    """Return transactions for a user, optionally filtered by account.

    Args:
        db: Async database session.
        user_id: Owner user ID (for authorization via account ownership).
        account_id: If provided, filter to this account only.

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

    result = await db.execute(query)
    return list(result.scalars().all())


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
