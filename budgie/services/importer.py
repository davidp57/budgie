"""Import service — deduplication and transaction persistence."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.importers.base import ImportedTransaction
from budgie.models.account import Account
from budgie.models.transaction import Transaction
from budgie.services.crypto import encrypt_str


class ImportResult(BaseModel):
    """Result of a :func:`confirm_import` call.

    Attributes:
        imported: Number of new transactions written to the database.
        duplicates: Number of transactions skipped due to duplicate
            ``import_hash``.
    """

    imported: int
    duplicates: int


async def confirm_import(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    transactions: list[ImportedTransaction],
    session_key: bytes | None = None,
) -> ImportResult:
    """Persist a list of parsed transactions, skipping duplicates.

    Transactions are considered duplicates if their ``import_hash``
    already exists in the ``transactions`` table.  Deduplication is
    performed in Python (one SELECT per transaction) rather than relying
    solely on the database unique constraint, so that the caller always
    receives accurate counts.

    When a transaction carries a ``virtual_linked_id``, the corresponding
    planned transaction is marked as ``status='reconciled'`` and the
    new real transaction records the link.

    Args:
        db: Active async SQLAlchemy session.
        account_id: Database ID of the target account.
        user_id: Owner user ID (ownership check).
        transactions: Parsed transactions to import.
        session_key: AES-256-GCM encryption key, or None if not unlocked.

    Returns:
        An :class:`ImportResult` with ``imported`` and ``duplicates``
        counts.

    Raises:
        PermissionError: If ``account_id`` does not belong to ``user_id``.
    """
    # Verify account ownership before inserting any data
    account_result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == user_id)
    )
    if account_result.scalar_one_or_none() is None:
        raise PermissionError(
            f"Account {account_id} not found or does not belong to the current user."
        )
    imported = 0
    duplicates = 0

    for txn in transactions:
        result = await db.execute(
            select(Transaction).where(Transaction.import_hash == txn.import_hash)
        )
        if result.scalar_one_or_none() is not None:
            duplicates += 1
            continue

        db_txn = Transaction(
            account_id=account_id,
            date=txn.date,
            amount=txn.amount,
            memo=encrypt_str(txn.description, session_key),
            import_hash=txn.import_hash,
            status="real",
        )
        db.add(db_txn)

        # If linked to a planned transaction, mark it as realized
        # Only reconcile virtual transactions owned by the same user (IDOR fix)
        if txn.virtual_linked_id is not None:
            planned_result = await db.execute(
                select(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .where(
                    Transaction.id == txn.virtual_linked_id,
                    Transaction.status == "planned",
                    Account.user_id == user_id,
                )
            )
            planned_txn = planned_result.scalar_one_or_none()
            if planned_txn is not None:
                planned_txn.status = "reconciled"

        imported += 1

    if imported > 0:
        await db.commit()

    return ImportResult(imported=imported, duplicates=duplicates)
