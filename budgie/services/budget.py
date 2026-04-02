"""Budget allocation CRUD service."""

from collections import defaultdict

from sqlalchemy import and_, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category
from budgie.models.envelope import Envelope, envelope_categories
from budgie.models.transaction import Transaction
from budgie.schemas.budget import (
    BudgetAllocationUpdate,
    EnvelopeLineRead,
    IncomeProposal,
    IncomeProposalsResponse,
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
        return MonthBudgetResponse(
            month=month, to_be_budgeted=0, total_available=0, envelopes=[]
        )

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

    # 2b. Sticky-budget inheritance: for rollover=False envelopes with no current-month
    #     allocation, inherit the budgeted amount from the most recent prior month.
    #     This makes regular budgets "sticky" — they persist until changed explicitly.
    no_alloc_non_rollover_ids = [
        env.id
        for env in envelopes
        if not env.rollover and env.id not in budgeted_this_month
    ]
    inherited_budgeted: dict[int, int] = {}
    if no_alloc_non_rollover_ids:
        max_prior_subq = (
            select(
                BudgetAllocation.envelope_id,
                func.max(BudgetAllocation.month).label("max_month"),
            )
            .where(
                BudgetAllocation.envelope_id.in_(no_alloc_non_rollover_ids),
                BudgetAllocation.month < month,
            )
            .group_by(BudgetAllocation.envelope_id)
            .subquery()
        )
        prior_alloc_result = await db.execute(
            select(BudgetAllocation.envelope_id, BudgetAllocation.budgeted).join(
                max_prior_subq,
                and_(
                    BudgetAllocation.envelope_id == max_prior_subq.c.envelope_id,
                    BudgetAllocation.month == max_prior_subq.c.max_month,
                ),
            )
        )
        inherited_budgeted = {row[0]: row[1] for row in prior_alloc_result.all()}

    # Effective budgeted = inherited (from prior month) OR explicit (this month).
    # Actual allocations always take precedence over inherited ones.
    effective_budgeted: dict[int, int] = {**inherited_budgeted, **budgeted_this_month}

    # 3. Activity this month per category (signed amounts, virtual included)
    #    Only for transactions WITHOUT a direct envelope_id (fallback path)
    activity_by_cat: dict[int, int] = {}
    cum_activity_by_cat: dict[int, int] = {}

    if all_cat_ids:
        act_result = await db.execute(
            select(Transaction.category_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.category_id.in_(all_cat_ids),
                Transaction.envelope_id.is_(None),
                func.strftime("%Y-%m", Transaction.date) == month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.category_id)
        )
        activity_by_cat = {row[0]: row[1] for row in act_result.all()}

        # 4. Cumulative activity per category
        #    (all months ≤ current, no direct envelope_id)
        cum_act_result = await db.execute(
            select(Transaction.category_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.category_id.in_(all_cat_ids),
                Transaction.envelope_id.is_(None),
                func.strftime("%Y-%m", Transaction.date) <= month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.category_id)
        )
        cum_activity_by_cat = {row[0]: row[1] for row in cum_act_result.all()}

    # 3b. Activity this month via direct envelope_id (manual expenses path)
    direct_activity_this_month: dict[int, int] = {}
    direct_cum_activity: dict[int, int] = {}
    if env_ids:
        direct_act_result = await db.execute(
            select(Transaction.envelope_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.envelope_id.in_(env_ids),
                func.strftime("%Y-%m", Transaction.date) == month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.envelope_id)
        )
        direct_activity_this_month = {row[0]: row[1] for row in direct_act_result.all()}

        # 4b. Cumulative activity via direct envelope_id
        direct_cum_act_result = await db.execute(
            select(Transaction.envelope_id, func.sum(Transaction.amount))
            .join(Account, Transaction.account_id == Account.id)
            .where(
                Transaction.envelope_id.in_(env_ids),
                func.strftime("%Y-%m", Transaction.date) <= month,
                Account.user_id == user_id,
            )
            .group_by(Transaction.envelope_id)
        )
        direct_cum_activity = {row[0]: row[1] for row in direct_cum_act_result.all()}

    # Aggregate activity per envelope (category path)
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
    # Add direct envelope_id path
    for env_id, amount in direct_activity_this_month.items():
        activity_this_month[env_id] += int(amount)
    for env_id, amount in direct_cum_activity.items():
        cum_activity[env_id] += int(amount)

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

    # 6. Income this month:
    #    a) positive uncategorised transactions dated in this month, OR
    #    b) transactions from any date marked with income_for_month = month
    #       (N+1 mode: real income from M-1 assigned to this month)
    income_row = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.category_id.is_(None),
            Transaction.amount > 0,
            Account.user_id == user_id,
            (
                (func.strftime("%Y-%m", Transaction.date) == month)
                | (Transaction.income_for_month == month)
            ),
        )
    )
    income: int = income_row.scalar_one()

    # 7. Total effective budgeted this month (actual + inherited) for to_be_budgeted.
    #    Inherited allocations count as committed income just like explicit ones.
    total_budgeted: int = sum(effective_budgeted.values())

    # Build envelope lines
    # Count all transactions per envelope for the month.
    # A transaction belongs to an envelope if:
    #   1. envelope_id = env.id (directly assigned), OR
    #   2. envelope_id IS NULL but category_id is in the envelope's categories
    #      (e.g. created via pointage with only a category set)
    env_ids = [env.id for env in envelopes]
    expense_counts: dict[int, int] = {}
    if env_ids:
        resolved_env_id = case(
            (Transaction.envelope_id.isnot(None), Transaction.envelope_id),
            else_=envelope_categories.c.envelope_id,
        )
        count_result = await db.execute(
            select(resolved_env_id, func.count(Transaction.id))
            .join(Account, Transaction.account_id == Account.id)
            .outerjoin(
                envelope_categories,
                and_(
                    Transaction.category_id == envelope_categories.c.category_id,
                    Transaction.envelope_id.is_(None),
                ),
            )
            .where(
                resolved_env_id.in_(env_ids),
                func.strftime("%Y-%m", Transaction.date) == month,
                Account.user_id == user_id,
            )
            .group_by(resolved_env_id)
        )
        expense_counts = {
            row[0]: row[1] for row in count_result.all() if row[0] is not None
        }

    envelope_lines = []
    for env in envelopes:
        b = effective_budgeted.get(env.id, 0)
        a = int(activity_this_month.get(env.id, 0))
        is_inherited = env.id in inherited_budgeted
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
                envelope_type=env.envelope_type,
                emoji=env.emoji,
                color_index=env.color_index,
                rollover=env.rollover,
                target_amount=env.target_amount,
                categories=cats,
                budgeted=b,
                activity=a,
                available=available,
                expense_count=expense_counts.get(env.id, 0),
                is_budget_inherited=is_inherited,
            )
        )

    total_available = sum(line.available for line in envelope_lines)

    return MonthBudgetResponse(
        month=month,
        to_be_budgeted=income - total_budgeted,
        total_available=total_available,
        envelopes=envelope_lines,
    )


async def upsert_allocation(
    db: AsyncSession,
    envelope_id: int,
    month: str,
    schema: BudgetAllocationUpdate,
    user_id: int,
) -> BudgetAllocation:
    """Create or update a budget allocation for an envelope and month.

    Args:
        db: Async database session.
        envelope_id: Envelope to allocate for.
        month: Budget month in YYYY-MM format.
        schema: Allocation update schema.
        user_id: Owner user ID (for envelope ownership check).

    Returns:
        Created or updated BudgetAllocation instance.

    Raises:
        PermissionError: If ``envelope_id`` does not belong to ``user_id``.
    """
    # Verify envelope ownership before writing
    env_result = await db.execute(
        select(Envelope).where(Envelope.id == envelope_id, Envelope.user_id == user_id)
    )
    if env_result.scalar_one_or_none() is None:
        raise PermissionError(
            f"Envelope {envelope_id} not found or does not belong to the current user."
        )

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


def _previous_month(month: str) -> str:
    """Return the previous month in YYYY-MM format.

    Args:
        month: Current month string in YYYY-MM format.

    Returns:
        Previous month as YYYY-MM string.
    """
    year, m = int(month[:4]), int(month[5:7])
    return f"{year - 1}-12" if m == 1 else f"{year}-{m - 1:02d}"


async def assign_income_to_month(
    db: AsyncSession,
    transaction_ids: list[int],
    month: str,
    user_id: int,
) -> int:
    """Mark real transactions as income for a specific budget month (N+1 mode).

    Instead of creating virtual transactions, this tags existing transactions
    from M-1 so their amount is counted in the target month ``to_be_budgeted``.
    Existing ``income_for_month`` tags on those transactions are replaced.

    Args:
        db: Async database session.
        transaction_ids: IDs of transactions to tag.
        month: Target budget month (YYYY-MM).
        user_id: Must own the account of each transaction (security check).

    Returns:
        Number of transactions updated.
    """
    if not transaction_ids:
        return 0

    result = await db.execute(
        select(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Transaction.id.in_(transaction_ids),
            Account.user_id == user_id,
        )
    )
    transactions = list(result.scalars().all())
    if not transactions:
        return 0

    # Delete any stale virtual income transactions for this month from the same
    # accounts (created by a previous Prévisionnel-mode run) to avoid
    # double-counting when the user switches to N+1 mode.
    account_ids = {txn.account_id for txn in transactions}
    await db.execute(
        delete(Transaction).where(
            Transaction.account_id.in_(account_ids),
            Transaction.status == "planned",
            Transaction.category_id.is_(None),
            Transaction.amount > 0,
            func.strftime("%Y-%m", Transaction.date) == month,
        )
    )

    for txn in transactions:
        txn.income_for_month = month
        db.add(txn)
    await db.commit()
    return len(transactions)


async def get_income_proposals(
    db: AsyncSession,
    month: str,
    user_id: int,
    threshold_centimes: int = 200_000,
) -> IncomeProposalsResponse:
    """Return income proposals drawn from positive transactions of M-1.

    Queries all positive transactions in the previous month from accounts owned
    by the user with an amount >= threshold_centimes, ordered by amount descending.
    These are candidates to be repeated as virtual income transactions in the
    current month.

    Args:
        db: Async database session.
        month: Current budget month in YYYY-MM format.
        user_id: Owner user ID.
        threshold_centimes: Minimum amount to include a transaction (default 200 000
            centimes = 2 000.00 €).

    Returns:
        IncomeProposalsResponse with list of candidate income transactions.
    """
    prev = _previous_month(month)

    result = await db.execute(
        select(
            Transaction.id,
            Transaction.date,
            Transaction.amount,
            Transaction.memo,
            Transaction.account_id,
        )
        .join(Account, Transaction.account_id == Account.id)
        .where(
            Account.user_id == user_id,
            Transaction.amount >= threshold_centimes,
            func.strftime("%Y-%m", Transaction.date) == prev,
        )
        .order_by(Transaction.amount.desc())
    )
    rows = result.all()

    proposals = [
        IncomeProposal(
            transaction_id=row[0],
            date=str(row[1]),
            amount=row[2],
            memo=row[3],
            account_id=row[4],
        )
        for row in rows
    ]

    return IncomeProposalsResponse(
        month=month,
        previous_month=prev,
        threshold_centimes=threshold_centimes,
        proposals=proposals,
    )
