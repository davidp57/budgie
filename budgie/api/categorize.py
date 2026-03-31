"""Categorization API router — POST /api/categorize."""

from fastapi import APIRouter

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.categorizer import (
    BatchCategorizeRequest,
    BatchCategorizeResponse,
    CategorizeResult,
)
from budgie.services.categorizer import categorize_transaction

router = APIRouter(prefix="/api/categorize", tags=["categorize"])


@router.post("", response_model=BatchCategorizeResponse)
async def categorize_batch(
    body: BatchCategorizeRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> BatchCategorizeResponse:
    """Categorize a batch of transactions for the authenticated user.

    Applies a two-step engine:

    1. **Payee auto-category** — if the payee name matches a known
       :class:`~budgie.models.payee.Payee` record with an
       ``auto_category_id``, that category is returned with confidence
       ``"auto"``.
    2. **Rule matching** — :class:`~budgie.models.category_rule.CategoryRule`
       rows are evaluated in descending priority order.  The first matching
       rule determines the category (confidence ``"rule"``).
    3. If neither step matches, ``category_id=None`` with confidence
       ``"none"`` is returned.

    Args:
        body: Batch request with a list of transactions to categorize.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        :class:`~budgie.schemas.categorizer.BatchCategorizeResponse` with
        one result per input transaction, in the same order.
    """
    results: list[CategorizeResult] = []
    for txn in body.transactions:
        result = await categorize_transaction(
            db,
            current_user.id,
            txn.payee_name,
            txn.memo,
            txn.amount,
        )
        results.append(result)
    return BatchCategorizeResponse(results=results)
