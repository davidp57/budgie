"""Data reset API router — wipe all transactions and category rules."""

from __future__ import annotations

from fastapi import APIRouter

from budgie.api.deps import CurrentUser, DBSession
from budgie.services import data_reset as svc

router = APIRouter(prefix="/api/user", tags=["user"])


@router.delete("/reset", response_model=dict[str, int])
async def reset_user_data(
    db: DBSession,
    current_user: CurrentUser,
) -> dict[str, int]:
    """Delete all transactions and category rules for the authenticated user.

    Transactions are deleted first (splits cascade, reconciliation links are
    set to NULL), then category rules.  Accounts, envelopes, and budget
    allocations are preserved.

    Args:
        db: Database session.
        current_user: JWT-authenticated user.

    Returns:
        Counts of deleted rows: ``transactions_deleted`` and ``rules_deleted``.
    """
    return await svc.reset_user_data(db, current_user.id)
