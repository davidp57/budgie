"""Transaction CRUD service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from budgie.models.account import Account
from budgie.models.transaction import Transaction
from budgie.schemas.transaction import TransactionCreate, TransactionUpdate
from budgie.services.crypto import decrypt_str, encrypt_str


async def get_transactions(
    db: AsyncSession,
    user_id: int,
    account_id: int | None = None,
    status: str | None = None,
    month: str | None = None,
    category_ids: list[int] | None = None,
    envelope_id: int | None = None,
    expenses_only: bool = False,
    limit: int | None = None,
    offset: int | None = None,
    session_key: bytes | None = None,
) -> list[Transaction]:
    """Return transactions for a user, optionally filtered and paginated.

    Args:
        db: Async database session.
        user_id: Owner user ID (for authorization via account ownership).
        account_id: If provided, filter to this account only.
        status: If provided, filter by transaction status (planned/real/reconciled).
        month: If provided, filter to transactions in this YYYY-MM month only.
        category_ids: If provided, filter to transactions whose category_id is
            in this list. Pass an empty list to return uncategorised transactions
            only.
        envelope_id: If provided, filter to transactions with this direct
            envelope_id.
        expenses_only: If True, return only manually-created budget expenses
            (transactions where import_hash IS NULL).
        limit: Maximum number of rows to return. None means no limit.
        offset: Number of rows to skip before returning. None means 0.
        session_key: AES-256-GCM decryption key, or None if not unlocked.

    Returns:
        List of Transaction instances ordered by date descending.
    """
    query = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Account.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
    )
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if status is not None:
        query = query.where(Transaction.status == status)
    if month is not None:
        query = query.where(func.strftime("%Y-%m", Transaction.date) == month)
    if category_ids is not None:
        if not category_ids:
            query = query.where(Transaction.category_id.is_(None))
        else:
            query = query.where(Transaction.category_id.in_(category_ids))
    if envelope_id is not None:
        query = query.where(Transaction.envelope_id == envelope_id)
    if expenses_only:
        query = query.where(Transaction.import_hash.is_(None))
    if offset is not None:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    result = await db.execute(query)
    txns = list(result.scalars().all())
    for txn in txns:
        set_committed_value(txn, "memo", decrypt_str(txn.memo, session_key))
    return txns


async def count_unassigned_expenses(
    db: AsyncSession,
    user_id: int,
) -> int:
    """Count manually-created expense transactions with no envelope assigned.

    These are "Hors budget" expenses: manually created (import_hash IS NULL),
    not created during pointage (reconciled_with_id IS NULL),
    and not linked to any envelope (category may or may not be set).

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        Count of unassigned expense transactions.
    """
    result = await db.execute(
        select(func.count(Transaction.id))
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Transaction.envelope_id.is_(None),
            Transaction.import_hash.is_(None),
            Transaction.reconciled_with_id.is_(None),
        )
    )
    return result.scalar_one()


async def get_planned_unlinked(
    db: AsyncSession,
    user_id: int,
    session_key: bytes | None = None,
) -> list[Transaction]:
    """Return all unlinked (pending) planned transactions for a user.

    These are planned transactions that have not yet been matched to a
    real imported transaction.

    Args:
        db: Async database session.
        user_id: Owner user ID.
        session_key: AES-256-GCM decryption key, or None if not unlocked.

    Returns:
        List of pending planned Transaction instances ordered by date.
    """
    query = (
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Transaction.status == "planned",
        )
        .order_by(Transaction.date.asc())
    )
    result = await db.execute(query)
    txns = list(result.scalars().all())
    for txn in txns:
        set_committed_value(txn, "memo", decrypt_str(txn.memo, session_key))
    return txns


async def link_planned(
    db: AsyncSession,
    real_txn: Transaction,
    planned_id: int,
    user_id: int,
) -> Transaction:
    """Link a real transaction to a planned one, marking the planned as reconciled.

    Marks the planned transaction as ``status='reconciled'``.

    Args:
        db: Async database session.
        real_txn: The real (imported) transaction.
        planned_id: ID of the planned transaction to mark as realized.
        user_id: Owner user ID (for authorization).

    Returns:
        Updated real Transaction instance.

    Raises:
        ValueError: If the planned transaction is not found or not owned by user.
    """
    planned_txn = await get_transaction(db, planned_id, user_id)
    if planned_txn is None or planned_txn.status != "planned":
        raise ValueError(f"Planned transaction {planned_id} not found")

    planned_txn.status = "reconciled"
    await db.commit()
    await db.refresh(real_txn)
    return real_txn


async def get_transaction(
    db: AsyncSession,
    transaction_id: int,
    user_id: int,
    session_key: bytes | None = None,
) -> Transaction | None:
    """Fetch a single transaction by ID, scoped to the user.

    Args:
        db: Async database session.
        transaction_id: Transaction primary key.
        user_id: Owner user ID.
        session_key: AES-256-GCM decryption key, or None if not unlocked.

    Returns:
        Transaction if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(Transaction.id == transaction_id, Account.user_id == user_id)
    )
    txn = result.scalar_one_or_none()
    if txn is not None:
        set_committed_value(txn, "memo", decrypt_str(txn.memo, session_key))
    return txn


async def create_transaction(
    db: AsyncSession,
    schema: TransactionCreate,
    user_id: int,
    session_key: bytes | None = None,
) -> Transaction:
    """Create a new transaction.

    Args:
        db: Async database session.
        schema: Validated transaction creation schema.
        user_id: Owner user ID (for account ownership check).
        session_key: AES-256-GCM encryption key, or None if not unlocked.

    Returns:
        Newly created Transaction instance.

    Raises:
        PermissionError: If ``schema.account_id`` does not belong to ``user_id``.
    """
    # Verify account ownership before creating the transaction
    account_result = await db.execute(
        select(Account).where(
            Account.id == schema.account_id, Account.user_id == user_id
        )
    )
    if account_result.scalar_one_or_none() is None:
        raise PermissionError(
            f"Account {schema.account_id} not found or does not belong"
            " to the current user."
        )

    deprecated_fields = {"cleared", "is_virtual", "virtual_linked_id"}

    data = {k: v for k, v in schema.model_dump().items() if k not in deprecated_fields}
    data["memo"] = encrypt_str(data.get("memo"), session_key)
    txn = Transaction(**data)
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    set_committed_value(txn, "memo", decrypt_str(txn.memo, session_key))
    return txn


async def update_transaction(
    db: AsyncSession,
    txn: Transaction,
    schema: TransactionUpdate,
    session_key: bytes | None = None,
) -> Transaction:
    """Partially update a transaction.

    Args:
        db: Async database session.
        txn: Existing Transaction instance.
        schema: Partial update schema.
        session_key: AES-256-GCM encryption key, or None if not unlocked.

    Returns:
        Updated Transaction instance.
    """
    _allowed_fields = {
        "date",
        "payee_id",
        "category_id",
        "envelope_id",
        "amount",
        "memo",
        "status",
        "income_for_month",
    }
    for field, value in schema.model_dump(exclude_unset=True).items():
        if field in _allowed_fields:
            if field == "memo":
                value = encrypt_str(value, session_key)
            setattr(txn, field, value)
    await db.commit()
    await db.refresh(txn)
    set_committed_value(txn, "memo", decrypt_str(txn.memo, session_key))
    return txn


async def delete_transaction(db: AsyncSession, txn: Transaction) -> None:
    """Delete a transaction.

    Args:
        db: Async database session.
        txn: Transaction instance to delete.
    """
    await db.delete(txn)
    await db.commit()
