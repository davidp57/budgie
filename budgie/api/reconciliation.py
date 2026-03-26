"""Reconciliation (pointage) API router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.reconciliation import (
    ClotureRequest,
    ClotureResponse,
    LinkRead,
    LinkRequest,
    ReconciliationViewResponse,
    SuggestionRead,
)
from budgie.services import reconciliation as svc

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.get("/view", response_model=ReconciliationViewResponse)
async def get_reconciliation_view(
    account_id: int,
    month: str,
    db: DBSession,
    current_user: CurrentUser,
) -> ReconciliationViewResponse:
    """Return the full reconciliation view for an account and month.

    Args:
        account_id: Account to reconcile.
        month: Month in YYYY-MM format.
        db: Database session.
        current_user: Authenticated user.
    """
    try:
        return await svc.get_view(db, current_user.id, account_id, month)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.get("/suggestions", response_model=list[SuggestionRead])
async def get_suggestions(
    account_id: int,
    month: str,
    db: DBSession,
    current_user: CurrentUser,
) -> list[SuggestionRead]:
    """Return rule-based matching suggestions for unlinked transactions.

    Args:
        account_id: Account to analyse.
        month: Month in YYYY-MM format.
        db: Database session.
        current_user: Authenticated user.
    """
    try:
        return await svc.get_suggestions(db, current_user.id, account_id, month)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post("/link", response_model=LinkRead, status_code=status.HTTP_201_CREATED)
async def create_link(
    req: LinkRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> LinkRead:
    """Create a reconciliation link between a bank tx and a budget expense.

    Args:
        req: Link request payload.
        db: Database session.
        current_user: Authenticated user.
    """
    try:
        return await svc.link(db, current_user.id, req)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.delete("/link/{bank_tx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    bank_tx_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Remove the reconciliation link for a bank transaction.

    Args:
        bank_tx_id: Bank transaction ID whose link to remove.
        db: Database session.
        current_user: Authenticated user.
    """
    await svc.unlink(db, current_user.id, bank_tx_id=bank_tx_id)


@router.post("/cloture", response_model=ClotureResponse)
async def cloture(
    req: ClotureRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ClotureResponse:
    """Finalise a reconciliation session.

    Marks all linked pairs as reconciled.

    Args:
        req: Clôture request.
        db: Database session.
        current_user: Authenticated user.
    """
    try:
        return await svc.cloture(db, current_user.id, req)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
