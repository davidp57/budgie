"""Budget allocations router."""

from fastapi import APIRouter

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.budget import (
    BudgetAllocationRead,
    BudgetAllocationUpdate,
    BudgetLineInput,
    MonthBudgetResponse,
)
from budgie.services.budget import get_month_budget_view, upsert_allocation

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("/{month}", response_model=MonthBudgetResponse)
async def get_budget(
    month: str,
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
    month: str,
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
        allocation = await upsert_allocation(
            db,
            envelope_id=line.envelope_id,
            month=month,
            schema=BudgetAllocationUpdate(budgeted=line.budgeted),
        )
        results.append(BudgetAllocationRead.model_validate(allocation))
    return results
