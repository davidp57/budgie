"""Budget allocation CRUD service."""

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category
from budgie.models.envelope import Envelope
from budgie.models.transaction import Transaction
from budgie.schemas.budget import (
    BudgetAllocationUpdate,
    EnvelopeLineRead,
    MonthBudgetResponse,
)
from budgie.schemas.envelope import CategoryRef


async def get_month_budget_view(
    db: AsyncSession, month: str, user_id: int
) -> MonthBudgetResponse:
    """Return the full envelope budget view for a given month.

    Computes per-envelope budgeted/activity/available amounts and the global
    to_be_budgeted figure (income received minus total allocated this month).

    - ``budgeted``: BudgetAllocation.budgeted for this specific month (0 if none).
    - ``activity``: sum of all transactions (incl. virtual) for this month across
      all categories linked to the envelope, from accounts owned by the user.
    - ``available``:
      - rollover=True:  cumulative Σ(budgeted) + Σ(activity) over all months ≤ month.
      - rollover=False: budgeted_this_month + activity_this_month (resets each month).
    - ``to_be_budgeted``: sum of positive uncategorised transactions this month
      minus sum of all budgeted allocations this month.

    Args:
        db: Async database session.
        month: Budget month in YYYY-MM format.
        user_id: Owner user ID.

    Returns:
        MonthBudgetResponse with envelopes list and to_be_budgeted.
    """
    # 1. All envelopes for the user, ordered for UI display, categories eagerly loaded
    env_result = await db.execute(
        select(Envelope)
        .options(selectinload(Envelope.categories).selectinload(Category.group))
        .where(Envelope.user_id == user_id)
        .order_by(Envelope.sort_order, Envelope.id)
    )
    envelopes = list(env_result.scalars().all())

    if not envelopes:
        return MonthBudgetResponse(month=month, to_be_budgeted=0, envelopes=[])

    env_ids = [env.id for env in envelopes]

    # Build category_id → envelope_id mapping (each category belongs to ≤ 1 envelope)
    cat_to_env: dict[int, int] = {
        c.id: env.id for env in envelopes for c in env.categories
    }
    all_cat_ids = list(cat_to_env.keys())

    # 2. Budgeted this month per envelope
    budgeted_result = await db.execute(
        select(BudgetAllocation.envelope_id, BudgetAllocation.budgeted).where(
            BudgetAllocation.envelope_id.in_(env_ids),
            BudgetAllocation.month == month,
        )
    )
    budgeted_this_month: dict[int, int] = {
        row[0]: row[1] for row in budgeted_result.all()
    }

    # 3. Activity this month per category (signed amounts, virtual included)
    activity_by_cat: dict[int, int] = {}
    cum_activity_by_cat: dict[int, int] = {}

    if all_cat_ids:
        act_result = await db.execute(
            select(Transaction.category_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.category_id.in_(all_cat_ids),
                func.strftime("%Y-%m", Transaction.date) == month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.category_id)
        )
        activity_by_cat = {row[0]: row[1] for row in act_result.all()}

        # 4. Cumulative activity per category (all months ≤ current)
        cum_act_result = await db.execute(
            select(Transaction.category_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.category_id.in_(all_cat_ids),
                func.strftime("%Y-%m", Transaction.date) <= month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.category_id)
        )
        cum_activity_by_cat = {row[0]: row[1] for row in cum_act_result.all()}

    # Aggregate activity per envelope
    activity_this_month: dict[int, int] = defaultdict(int)
    cum_activity: dict[int, int] = defaultdict(int)
    for cat_id, amount in activity_by_cat.items():
        env_id = cat_to_env.get(cat_id)
        if env_id is not None:
            activity_this_month[env_id] += amount
    for cat_id, amount in cum_activity_by_cat.items():
        env_id = cat_to_env.get(cat_id)
        if env_id is not None:
            cum_activity[env_id] += amount

    # 5. Cumulative budgeted per envelope (for rollover)
    cum_budgeted_result = await db.execute(
        select(BudgetAllocation.envelope_id, func.sum(BudgetAllocation.budgeted))
        .where(
            BudgetAllocation.envelope_id.in_(env_ids),
            BudgetAllocation.month <= month,
        )
        .group_by(BudgetAllocation.envelope_id)
    )
    cum_budgeted: dict[int, int] = {row[0]: row[1] for row in cum_budgeted_result.all()}

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
            BudgetAllocation.envelope_id.in_(env_ids),
            BudgetAllocation.month == month,
        )
    )
    total_budgeted: int = total_budgeted_row.scalar_one()

    # Build envelope lines
    envelope_lines = []
    for env in envelopes:
        b = budgeted_this_month.get(env.id, 0)
        a = int(activity_this_month.get(env.id, 0))
        if env.rollover:
            available = int(cum_budgeted.get(env.id, 0)) + int(
                cum_activity.get(env.id, 0)
            )
        else:
            available = b + a

        cats = [
            CategoryRef(id=c.id, name=c.name, group_name=c.group.name)
            for c in sorted(
                env.categories,
                key=lambda x: (x.group.sort_order, x.sort_order),
            )
        ]
        envelope_lines.append(
            EnvelopeLineRead(
                envelope_id=env.id,
                envelope_name=env.name,
                rollover=env.rollover,
                categories=cats,
                budgeted=b,
                activity=a,
                available=available,
            )
        )

    return MonthBudgetResponse(
        month=month,
        to_be_budgeted=income - total_budgeted,
        envelopes=envelope_lines,
    )


async def upsert_allocation(
    db: AsyncSession,
    envelope_id: int,
    month: str,
    schema: BudgetAllocationUpdate,
) -> BudgetAllocation:
    """Create or update a budget allocation for an envelope and month.

    Args:
        db: Async database session.
        envelope_id: Envelope to allocate for.
        month: Budget month in YYYY-MM format.
        schema: Allocation update schema.

    Returns:
        Created or updated BudgetAllocation instance.
    """
    result = await db.execute(
        select(BudgetAllocation).where(
            BudgetAllocation.envelope_id == envelope_id,
            BudgetAllocation.month == month,
        )
    )
    allocation = result.scalar_one_or_none()

    if allocation is None:
        allocation = BudgetAllocation(
            envelope_id=envelope_id,
            month=month,
            budgeted=schema.budgeted,
        )
        db.add(allocation)
    else:
        allocation.budgeted = schema.budgeted

    await db.commit()
    await db.refresh(allocation)
    return allocation


async def get_budget_month(
    db: AsyncSession, month: str, user_id: int
) -> list[BudgetAllocation]:
    """Return all budget allocations for a month, scoped to the user's envelopes.

    Args:
        db: Async database session.
        month: Budget month in YYYY-MM format.
        user_id: Owner user ID.

    Returns:
        List of BudgetAllocation instances for the given month.
    """
    result = await db.execute(
        select(BudgetAllocation)
        .join(Envelope, BudgetAllocation.envelope_id == Envelope.id)
        .where(BudgetAllocation.month == month, Envelope.user_id == user_id)
    )
    return list(result.scalars().all())
