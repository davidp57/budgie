"""Data reset service — wipe all expenses and category rules for a user.

Intended for development and testing convenience.  Every operation is scoped
to the authenticated user so no cross-user data is ever touched.

Terminology (mirrors the reconciliation module)
-----------------------------------------------
* **bank_tx**  — Transaction with ``import_hash`` set (imported from bank).
* **expense**  — Transaction with ``import_hash=None`` (budget entry / dépense).
* **link**     — ``expense.reconciled_with_id == bank_tx.id``.

The reset deletes **expenses** only.  Bank-imported transactions are preserved
so the import history is not lost.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.category_rule import CategoryRule
from budgie.models.transaction import SplitTransaction, Transaction


async def reset_user_data(
    db: AsyncSession,
    user_id: int,
) -> dict[str, int]:
    """Delete all expenses and category rules belonging to *user_id*.

    The operation is performed in the following order to respect FK constraints:

    1. Collect the account IDs owned by *user_id*.
    2. Collect the IDs of **expense** transactions (``import_hash IS NULL``)
       in those accounts.
    3. Delete ``split_transactions`` rows for those expenses (no DB-level
       cascade on this FK).
    4. Delete the expense transactions themselves.  The reconciliation link
       lives on the expense side (``expense.reconciled_with_id = bank_tx.id``),
       so deleting the expense row is sufficient — the bank_tx is untouched.
    5. Delete all ``category_rules`` owned by the user.

    Bank-imported transactions (``import_hash`` set) are **preserved**.

    Args:
        db: Async SQLAlchemy session.
        user_id: ID of the authenticated user whose data is wiped.

    Returns:
        A dict with keys ``transactions_deleted`` and ``rules_deleted``
        containing the respective row counts.
    """
    # ── 1. Collect account IDs for this user ──────────────────────────────
    account_ids_result = await db.execute(
        select(Account.id).where(Account.user_id == user_id)
    )
    account_ids = list(account_ids_result.scalars().all())

    expense_count = 0

    if account_ids:
        # ── 2. Collect expense IDs (import_hash IS NULL) ──────────────────
        expense_ids_result = await db.execute(
            select(Transaction.id).where(
                Transaction.account_id.in_(account_ids),
                Transaction.import_hash.is_(None),
            )
        )
        expense_ids = list(expense_ids_result.scalars().all())
        expense_count = len(expense_ids)

        if expense_ids:
            # ── 3. Delete split transactions (no DB-level cascade) ────────
            await db.execute(
                delete(SplitTransaction).where(
                    SplitTransaction.parent_id.in_(expense_ids)
                )
            )

            # ── 4. Delete the expenses ─────────────────────────────────────
            await db.execute(delete(Transaction).where(Transaction.id.in_(expense_ids)))

    # ── 5. Delete category rules ──────────────────────────────────────────
    # Count first (rowcount on async execute is not reliably typed by mypy)
    rules_count_result = await db.execute(
        select(func.count())
        .select_from(CategoryRule)
        .where(CategoryRule.user_id == user_id)
    )
    rules_count: int = rules_count_result.scalar_one()

    await db.execute(delete(CategoryRule).where(CategoryRule.user_id == user_id))

    await db.commit()

    return {
        "transactions_deleted": expense_count,
        "rules_deleted": rules_count,
    }
