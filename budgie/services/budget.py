"""Budget allocation CRUD service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category, CategoryGroup
from budgie.models.transaction import Transaction
from budgie.schemas.budget import (
    BudgetAllocationUpdate,
    EnvelopeLineRead,
    MonthBudgetResponse,
)


async def get_budget_month(
    db: AsyncSession, month: str, user_id: int
) -> list[BudgetAllocation]:
    """Return all budget allocations for a month, scoped to the user.

    Filters by categories belonging to the user's category groups.

    Args:
        db: Async database session.
        month: Budget month in YYYY-MM format.
        user_id: Owner user ID.

    Returns:
        List of BudgetAllocation instances for the given month.
    """
    result = await db.execute(
        select(BudgetAllocation)
        .join(Category, BudgetAllocation.category_id == Category.id)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(BudgetAllocation.month == month, CategoryGroup.user_id == user_id)
    )
    return list(result.scalars().all())


async def get_month_budget_view(
    db: AsyncSession, month: str, user_id: int
) -> MonthBudgetResponse:
    """Return the full envelope budget view for a given month.

    Computes per-category budgeted/activity/available amounts and the global
    to_be_budgeted figure (income received minus total allocated this month).

    - ``budgeted``: BudgetAllocation.budgeted for this specific month (0 if none).
    - ``activity``: sum of all transaction amounts (incl. virtual) for this month
      in this category, from accounts owned by the user.
    - ``available``: cumulative Σ(budgeted) + Σ(activity amounts) over all months
      up to and including ``month``.
    - ``to_be_budgeted``: sum of positive uncategorised transactions this month
      minus sum of all budgeted allocations this month.

    Args:
        db: Async database session.
        month: Budget month in YYYY-MM format.
        user_id: Owner user ID.

    Returns:
        MonthBudgetResponse with envelopes list and to_be_budgeted.
    """
    # 1. All non-hidden categories for the user, ordered for UI display
    cats_result = await db.execute(
        select(Category, CategoryGroup)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(CategoryGroup.user_id == user_id, Category.hidden.is_(False))
        .order_by(CategoryGroup.sort_order, Category.sort_order)
    )
    cat_rows = cats_result.all()

    if not cat_rows:
        return MonthBudgetResponse(month=month, to_be_budgeted=0, envelopes=[])

    cat_ids = [cat.id for cat, _ in cat_rows]

    # 2. Budgeted this month per category
    budgeted_result = await db.execute(
        select(BudgetAllocation.category_id, BudgetAllocation.budgeted).where(
            BudgetAllocation.category_id.in_(cat_ids),
            BudgetAllocation.month == month,
        )
    )
    budgeted_this_month: dict[int, int] = {
        row[0]: row[1] for row in budgeted_result.all()
    }

    # 3. Activity this month per category (signed amounts, virtual included)
    activity_result = await db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.category_id.in_(cat_ids),
            func.strftime("%Y-%m", Transaction.date) == month,
            Account.user_id == user_id,
        )
        .group_by(Transaction.category_id)
    )
    activity_this_month: dict[int, int] = {
        row[0]: row[1] for row in activity_result.all()
    }

    # 4. Cumulative budgeted per category (all months ≤ current)
    cum_budgeted_result = await db.execute(
        select(BudgetAllocation.category_id, func.sum(BudgetAllocation.budgeted))
        .where(
            BudgetAllocation.category_id.in_(cat_ids),
            BudgetAllocation.month <= month,
        )
        .group_by(BudgetAllocation.category_id)
    )
    cum_budgeted: dict[int, int] = {row[0]: row[1] for row in cum_budgeted_result.all()}

    # 5. Cumulative activity per category (all months ≤ current)
    cum_activity_result = await db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount))
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.category_id.in_(cat_ids),
            func.strftime("%Y-%m", Transaction.date) <= month,
            Account.user_id == user_id,
        )
        .group_by(Transaction.category_id)
    )
    cum_activity: dict[int, int] = {row[0]: row[1] for row in cum_activity_result.all()}

    # 6. Income this month: positive uncategorised transactions in user's accounts
    income_row = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.category_id.is_(None),
            Transaction.amount > 0,
            func.strftime("%Y-%m", Transaction.date) == month,
            Account.user_id == user_id,
        )
    )
    income: int = income_row.scalar_one()

    # 7. Total budgeted this month (for to_be_budgeted)
    total_budgeted_row = await db.execute(
        select(func.coalesce(func.sum(BudgetAllocation.budgeted), 0)).where(
            BudgetAllocation.category_id.in_(cat_ids),
            BudgetAllocation.month == month,
        )
    )
    total_budgeted: int = total_budgeted_row.scalar_one()

    # Build envelope list
    envelopes = [
        EnvelopeLineRead(
            category_id=cat.id,
            category_name=cat.name,
            group_id=group.id,
            group_name=group.name,
            budgeted=budgeted_this_month.get(cat.id, 0),
            activity=activity_this_month.get(cat.id, 0),
            # available = Σbudgeted + Σactivity (activity amounts are signed)
            available=cum_budgeted.get(cat.id, 0) + cum_activity.get(cat.id, 0),
        )
        for cat, group in cat_rows
    ]

    return MonthBudgetResponse(
        month=month,
        to_be_budgeted=income - total_budgeted,
        envelopes=envelopes,
    )


async def upsert_allocation(
    db: AsyncSession,
    category_id: int,
    month: str,
    schema: BudgetAllocationUpdate,
) -> BudgetAllocation:
    """Create or update a budget allocation for a category and month.

    Args:
        db: Async database session.
        category_id: Category to allocate for.
        month: Budget month in YYYY-MM format.
        schema: Allocation update schema.

    Returns:
        Created or updated BudgetAllocation instance.
    """
    result = await db.execute(
        select(BudgetAllocation).where(
            BudgetAllocation.category_id == category_id,
            BudgetAllocation.month == month,
        )
    )
    allocation = result.scalar_one_or_none()

    if allocation is None:
        allocation = BudgetAllocation(
            category_id=category_id,
            month=month,
            budgeted=schema.budgeted,
        )
        db.add(allocation)
    else:
        allocation.budgeted = schema.budgeted

    await db.commit()
    await db.refresh(allocation)
    return allocation
