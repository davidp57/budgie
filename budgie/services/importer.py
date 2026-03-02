"""Import service — deduplication and transaction persistence."""

from __future__ import annotations

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.importers.base import ImportedTransaction
from budgie.models.transaction import Transaction


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
    transactions: list[ImportedTransaction],
) -> ImportResult:
    """Persist a list of parsed transactions, skipping duplicates.

    Transactions are considered duplicates if their ``import_hash``
    already exists in the ``transactions`` table.  Deduplication is
    performed in Python (one SELECT per transaction) rather than relying
    solely on the database unique constraint, so that the caller always
    receives accurate counts.

    Args:
        db: Active async SQLAlchemy session.
        account_id: Database ID of the target account.
        transactions: Parsed transactions to import.

    Returns:
        An :class:`ImportResult` with ``imported`` and ``duplicates``
        counts.
    """
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
            memo=txn.description,
            import_hash=txn.import_hash,
            cleared="uncleared",
        )
        db.add(db_txn)
        imported += 1

    if imported > 0:
        await db.commit()

    return ImportResult(imported=imported, duplicates=duplicates)
