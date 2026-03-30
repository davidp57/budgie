"""Budget allocations router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.budget import (
    MONTH_PATTERN,
    AssignIncomeRequest,
    BudgetAllocationRead,
    BudgetAllocationUpdate,
    BudgetLineInput,
    IncomeProposalsResponse,
    MonthBudgetResponse,
)
from budgie.services.budget import (
    assign_income_to_month,
    get_income_proposals,
    get_month_budget_view,
    upsert_allocation,
)

router = APIRouter(prefix="/api/budget", tags=["budget"])

#: Reusable Path annotation that validates ``YYYY-MM`` format.
MonthPath = Annotated[str, Path(pattern=MONTH_PATTERN)]


@router.post("/{month}/assign-income", status_code=204)
async def assign_income(
    month: MonthPath,
    payload: AssignIncomeRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Tag real transactions from M-1 as income for this budget month (N+1 mode).

    Does not create virtual transactions. Instead marks existing transactions
    so their amounts count toward ``to_be_budgeted`` for the given month.

    Args:
        month: Target budget month (YYYY-MM).
        payload: List of transaction IDs to tag.
        db: Async database session.
        current_user: JWT-authenticated user.
    """
    await assign_income_to_month(db, payload.transaction_ids, month, current_user.id)


@router.get("/{month}/income-proposals", response_model=IncomeProposalsResponse)
async def list_income_proposals(
    month: MonthPath,
    db: DBSession,
    current_user: CurrentUser,
    threshold_centimes: int = 200_000,
) -> IncomeProposalsResponse:
    """Return income proposal candidates drawn from M-1 positive transactions.

    Returns all positive transactions from the previous month with amount >=
    threshold_centimes. These can be used to plan virtual income transactions
    for the current month.

    Args:
        month: Current budget month in YYYY-MM format.
        db: Async database session.
        current_user: JWT-authenticated user.
        threshold_centimes: Minimum amount to include (default 200 000 = 2 000.00 €).

    Returns:
        Income proposals ordered by amount descending.
    """
    return await get_income_proposals(db, month, current_user.id, threshold_centimes)


@router.get("/{month}", response_model=MonthBudgetResponse)
async def get_budget(
    month: MonthPath,
    db: DBSession,
    current_user: CurrentUser,
) -> MonthBudgetResponse:
    """Get the full envelope budget view for a given month.

    Returns per-envelope budgeted/activity/available amounts along with the
    global to_be_budgeted figure (income minus total allocated this month).

    Args:
        month: Budget month in YYYY-MM format.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Full month budget view with envelopes and to_be_budgeted.
    """
    return await get_month_budget_view(db, month, current_user.id)


@router.put("/{month}", response_model=list[BudgetAllocationRead])
async def set_budget(
    month: MonthPath,
    lines: list[BudgetLineInput],
    db: DBSession,
    current_user: CurrentUser,
) -> list[BudgetAllocationRead]:
    """Create or update budget allocations for a given month.

    Accepts a list of envelope_id + budgeted pairs and upserts each.

    Args:
        month: Budget month in YYYY-MM format.
        lines: List of budget line inputs.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of updated budget allocations.
    """
    results = []
    for line in lines:
        try:
            allocation = await upsert_allocation(
                db,
                envelope_id=line.envelope_id,
                month=month,
                schema=BudgetAllocationUpdate(budgeted=line.budgeted),
                user_id=current_user.id,
            )
        except PermissionError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
            ) from exc
        results.append(BudgetAllocationRead.model_validate(allocation))
    return results
