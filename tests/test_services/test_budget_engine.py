"""Tests for the budget engine service.

Tests envelope calculations: budgeted, activity, available,
and the to_be_budgeted month aggregate.

Architecture: Envelopes are the budget units. Categories are linked to at most
one envelope via the envelope_categories M2M table. Budget allocations target
envelopes (not categories).

TDD — tests written before implementation.
"""

import datetime

import pytest
from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category, CategoryGroup
from budgie.models.envelope import Envelope, envelope_categories
from budgie.models.transaction import Transaction
from budgie.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

# ── Helpers ──────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, username: str = "alice") -> User:
    """Create and persist a test user."""
    user = User(username=username, hashed_password="hashed")
    db.add(user)
    await db.flush()
    return user


async def _make_category(
    db: AsyncSession,
    user_id: int,
    name: str = "Food",
    group_name: str = "Expenses",
) -> tuple[Category, CategoryGroup]:
    """Create a category group + category scoped to user."""
    group = CategoryGroup(user_id=user_id, name=group_name, sort_order=0)
    db.add(group)
    await db.flush()
    cat = Category(group_id=group.id, name=name, sort_order=0)
    db.add(cat)
    await db.flush()
    return cat, group


async def _make_account(
    db: AsyncSession, user_id: int, name: str = "Checking"
) -> Account:
    """Create and persist a test account."""
    account = Account(
        user_id=user_id,
        name=name,
        account_type="checking",
        on_budget=True,
    )
    db.add(account)
    await db.flush()
    return account


async def _make_transaction(
    db: AsyncSession,
    account_id: int,
    date: datetime.date,
    amount: int,
    category_id: int | None = None,
    status: str = "real",
) -> Transaction:
    """Create and persist a test transaction."""
    txn = Transaction(
        account_id=account_id,
        date=date,
        amount=amount,
        category_id=category_id,
        status=status,
    )
    db.add(txn)
    await db.flush()
    return txn


async def _make_envelope(
    db: AsyncSession,
    user_id: int,
    name: str = "My Envelope",
    rollover: bool = False,
    sort_order: int = 0,
) -> Envelope:
    """Create and persist an envelope (with no categories)."""
    env = Envelope(user_id=user_id, name=name, rollover=rollover, sort_order=sort_order)
    db.add(env)
    await db.flush()
    return env


async def _link_category(db: AsyncSession, envelope_id: int, category_id: int) -> None:
    """Link a category to an envelope via the association table."""
    await db.execute(
        envelope_categories.insert(),
        [{"envelope_id": envelope_id, "category_id": category_id}],
    )
    await db.flush()


async def _make_allocation(
    db: AsyncSession, envelope_id: int, month: str, budgeted: int
) -> BudgetAllocation:
    """Create and persist a budget allocation for an envelope."""
    alloc = BudgetAllocation(envelope_id=envelope_id, month=month, budgeted=budgeted)
    db.add(alloc)
    await db.flush()
    return alloc


# ── Tests: envelope.budgeted ─────────────────────────────────────


async def test_budgeted_from_allocation(db_session: AsyncSession) -> None:
    """Envelope budgeted = BudgetAllocation.budgeted for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    env = await _make_envelope(db_session, user.id, "Food")
    await _make_allocation(db_session, env.id, "2026-01", budgeted=15000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 1
    line = view.envelopes[0]
    assert line.envelope_id == env.id
    assert line.budgeted == 15000


async def test_budgeted_zero_when_no_allocation(db_session: AsyncSession) -> None:
    """Envelope budgeted = 0 if no BudgetAllocation exists for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Transport")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 1
    assert view.envelopes[0].budgeted == 0


async def test_all_envelopes_appear_even_without_allocation(
    db_session: AsyncSession,
) -> None:
    """All user envelopes appear in the view, regardless of allocations."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Food")
    await _make_envelope(db_session, user.id, "Transport")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 2


# ── Tests: envelope.activity ─────────────────────────────────────


async def test_activity_sums_transactions_for_month(db_session: AsyncSession) -> None:
    """Activity = sum of real transactions for the month across envelope categories."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, "Groceries")
    env = await _make_envelope(db_session, user.id, "Food")
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 10), -3000, cat.id
    )
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 20), -2000, cat.id
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == -5000  # sum of two expenses


async def test_activity_includes_virtual_transactions(db_session: AsyncSession) -> None:
    """Virtual transactions count toward envelope activity."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, "Rent")
    env = await _make_envelope(db_session, user.id, "Housing")
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 1),
        -80000,
        cat.id,
        status="planned",
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == -80000


async def test_activity_sums_multiple_categories_per_envelope(
    db_session: AsyncSession,
) -> None:
    """Activity = sum of all categories linked to the envelope."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat1, _ = await _make_category(db_session, user.id, "Groceries", "Food")
    cat2, _ = await _make_category(db_session, user.id, "Restaurants", "Food")
    env = await _make_envelope(db_session, user.id, "Food Budget")
    await _link_category(db_session, env.id, cat1.id)
    await _link_category(db_session, env.id, cat2.id)
    account = await _make_account(db_session, user.id)

    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 5), -4000, cat1.id
    )
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 12), -1500, cat2.id
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == -5500  # -4000 + -1500


async def test_activity_zero_when_no_transactions(db_session: AsyncSession) -> None:
    """Activity = 0 when there are no transactions for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Savings")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == 0


async def test_activity_excludes_other_months(db_session: AsyncSession) -> None:
    """Transactions from other months do not count in this month's activity."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    env = await _make_envelope(db_session, user.id, "Misc")
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    # Transaction in February — should NOT appear in January activity
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 2, 5), -5000, cat.id
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == 0


# ── Tests: envelope.available ────────────────────────────────────


async def test_available_no_rollover_budgeted_minus_activity(
    db_session: AsyncSession,
) -> None:
    """rollover=False: available = budgeted_this_month + activity_this_month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    env = await _make_envelope(db_session, user.id, "Food", rollover=False)
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    await _make_allocation(db_session, env.id, "2026-01", budgeted=10000)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 15), -3000, cat.id
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].available == 7000  # 10000 - 3000


async def test_available_no_rollover_does_not_carry_previous_months(
    db_session: AsyncSession,
) -> None:
    """rollover=False: previous month surplus is NOT included in available."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    env = await _make_envelope(db_session, user.id, "Bills", rollover=False)
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    # January: budget 100€, spend 30€ → surplus 70€ (should NOT carry to Feb)
    await _make_allocation(db_session, env.id, "2026-01", budgeted=10000)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 10), -3000, cat.id
    )
    # February: budget 50€, spend 20€
    await _make_allocation(db_session, env.id, "2026-02", budgeted=5000)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 2, 10), -2000, cat.id
    )

    view = await get_month_budget_view(db_session, "2026-02", user.id)

    # available = 5000 - 2000 = 3000 (no carry-over)
    assert view.envelopes[0].available == 3000


async def test_available_rollover_cumulative_across_months(
    db_session: AsyncSession,
) -> None:
    """rollover=True: available cumulates all months up to current."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    env = await _make_envelope(db_session, user.id, "Emergency Fund", rollover=True)
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    # January: budget 100€, spend 30€ → leftover 70€
    await _make_allocation(db_session, env.id, "2026-01", budgeted=10000)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 1, 10), -3000, cat.id
    )
    # February: budget 50€, spend 20€ → leftover 30€
    await _make_allocation(db_session, env.id, "2026-02", budgeted=5000)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 2, 10), -2000, cat.id
    )

    view = await get_month_budget_view(db_session, "2026-02", user.id)

    # available = (10000 + 5000) + (-3000 + -2000) = 15000 - 5000 = 10000
    assert view.envelopes[0].available == 10000


async def test_available_future_months_not_counted(db_session: AsyncSession) -> None:
    """Allocations from future months do not affect current available."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    env = await _make_envelope(db_session, user.id, "Savings", rollover=True)

    await _make_allocation(db_session, env.id, "2026-01", budgeted=5000)
    # March allocation should NOT be counted when viewing January
    await _make_allocation(db_session, env.id, "2026-03", budgeted=9999)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].available == 5000


# ── Tests: to_be_budgeted ────────────────────────────────────────


async def test_to_be_budgeted_income_minus_total_budgeted(
    db_session: AsyncSession,
) -> None:
    """to_be_budgeted = sum(positive uncategorized) - sum(budgeted allocations)."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    env = await _make_envelope(db_session, user.id, "Expenses")
    account = await _make_account(db_session, user.id)

    # Income (positive, no category)
    await _make_transaction(db_session, account.id, datetime.date(2026, 1, 1), 200000)
    await _make_allocation(db_session, env.id, "2026-01", budgeted=150000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 50000  # 200000 - 150000


async def test_to_be_budgeted_zero_income_no_budget(db_session: AsyncSession) -> None:
    """to_be_budgeted = 0 when no income and no budget."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Misc")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 0


async def test_to_be_budgeted_negative_expenses_not_counted_as_income(
    db_session: AsyncSession,
) -> None:
    """Negative uncategorized transactions do not count as income."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Misc")
    acc = await _make_account(db_session, user.id)

    # Negative uncategorized transaction (e.g., bank fees) — NOT income
    await _make_transaction(db_session, acc.id, datetime.date(2026, 1, 5), -1000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 0


# ── Tests: user scoping ──────────────────────────────────────────


async def test_envelopes_scoped_to_user(db_session: AsyncSession) -> None:
    """Envelopes from another user do not appear in the budget view."""
    from budgie.services.budget import get_month_budget_view

    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    await _make_envelope(db_session, alice.id, "Alice Food")
    await _make_envelope(db_session, bob.id, "Bob Transport")

    alice_view = await get_month_budget_view(db_session, "2026-01", alice.id)
    bob_view = await get_month_budget_view(db_session, "2026-01", bob.id)

    assert len(alice_view.envelopes) == 1
    assert alice_view.envelopes[0].envelope_name == "Alice Food"
    assert len(bob_view.envelopes) == 1
    assert bob_view.envelopes[0].envelope_name == "Bob Transport"


async def test_activity_scoped_to_user_accounts(db_session: AsyncSession) -> None:
    """Transactions from another user's accounts don't affect activity."""
    from budgie.services.budget import get_month_budget_view

    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    cat, _ = await _make_category(db_session, alice.id)
    env = await _make_envelope(db_session, alice.id, "Food")
    await _link_category(db_session, env.id, cat.id)

    # Bob has an account that references Alice's category — should NOT count
    bob_account = await _make_account(db_session, bob.id, "Bob Checking")
    await _make_transaction(
        db_session, bob_account.id, datetime.date(2026, 1, 10), -5000, cat.id
    )

    alice_view = await get_month_budget_view(db_session, "2026-01", alice.id)

    assert alice_view.envelopes[0].activity == 0


# ── Tests: month metadata ────────────────────────────────────────


async def test_month_in_response(db_session: AsyncSession) -> None:
    """MonthBudgetResponse.month matches the requested month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)

    view = await get_month_budget_view(db_session, "2026-03", user.id)

    assert view.month == "2026-03"


async def test_empty_view_when_no_envelopes(db_session: AsyncSession) -> None:
    """Returns empty envelopes list when user has no envelopes."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes == []
    assert view.to_be_budgeted == 0


# ── Tests: envelope metadata ─────────────────────────────────────


async def test_envelope_contains_name_rollover_and_categories(
    db_session: AsyncSession,
) -> None:
    """EnvelopeLineRead includes name, rollover flag, and categories list."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    group = CategoryGroup(user_id=user.id, name="Household", sort_order=0)
    db_session.add(group)
    await db_session.flush()
    cat = Category(group_id=group.id, name="Electricity", sort_order=0)
    db_session.add(cat)
    await db_session.flush()
    env = await _make_envelope(db_session, user.id, "Bills", rollover=False)
    await _link_category(db_session, env.id, cat.id)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    line = view.envelopes[0]
    assert line.envelope_name == "Bills"
    assert line.rollover is False
    assert len(line.categories) == 1
    assert line.categories[0].name == "Electricity"
    assert line.categories[0].group_name == "Household"


async def test_envelope_with_no_categories_still_shown(
    db_session: AsyncSession,
) -> None:
    """Envelopes with no linked categories still appear in the budget view."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Uncategorized Fund")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 1
    assert view.envelopes[0].categories == []


async def test_to_be_budgeted_only_current_month_income(
    db_session: AsyncSession,
) -> None:
    """Income from other months does not affect to_be_budgeted for current month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_envelope(db_session, user.id, "Expenses")
    account = await _make_account(db_session, user.id)

    # December income — should NOT be counted in January
    await _make_transaction(db_session, account.id, datetime.date(2025, 12, 31), 300000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 0


@pytest.mark.parametrize(
    "month",
    ["2026-01", "2026-12", "2025-06"],
)
async def test_view_returns_correct_month_string(
    db_session: AsyncSession, month: str
) -> None:
    """MonthBudgetResponse.month is always the exact requested month string."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    view = await get_month_budget_view(db_session, month, user.id)
    assert view.month == month


# ── Tests: envelope_id direct path ───────────────────────────────


async def test_activity_via_direct_envelope_id(db_session: AsyncSession) -> None:
    """Transactions with envelope_id are counted in activity even without a category."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    env = await _make_envelope(db_session, user.id, "Cash Drawer")
    account = await _make_account(db_session, user.id)

    # Direct expense linked to envelope (no category_id)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 3, 10),
        amount=-3000,
        status="real",
        envelope_id=env.id,
    )
    db_session.add(txn)
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-03", user.id)

    assert len(view.envelopes) == 1
    assert view.envelopes[0].activity == -3000


async def test_activity_hybrid_category_and_direct(db_session: AsyncSession) -> None:
    """Activity sums both direct envelope_id and category-based transactions."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, "Groceries")
    env = await _make_envelope(db_session, user.id, "Food")
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    # Category-based transaction (fallback path)
    await _make_transaction(
        db_session, account.id, datetime.date(2026, 3, 1), -2000, category_id=cat.id
    )
    # Direct envelope transaction (no category, no envelope_id — NOT counted)
    await _make_transaction(db_session, account.id, datetime.date(2026, 3, 5), -1000)
    # Direct envelope transaction WITH envelope_id
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 3, 6),
        amount=-1500,
        status="real",
        envelope_id=env.id,
    )
    db_session.add(txn)
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-03", user.id)

    # -2000 (via category) + -1500 (direct envelope) = -3500
    assert view.envelopes[0].activity == -3500


async def test_direct_envelope_tx_not_double_counted(db_session: AsyncSession) -> None:
    """A transaction with envelope_id is NOT counted via category too."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, "Food")
    env = await _make_envelope(db_session, user.id, "Groceries")
    await _link_category(db_session, env.id, cat.id)
    account = await _make_account(db_session, user.id)

    # Transaction with BOTH category_id AND envelope_id
    # → should count only once (direct path)
    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 3, 1),
        amount=-5000,
        status="real",
        category_id=cat.id,
        envelope_id=env.id,
    )
    db_session.add(txn)
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-03", user.id)

    assert view.envelopes[0].activity == -5000  # not -10000


async def test_rollover_cumulative_with_direct_envelope_id(
    db_session: AsyncSession,
) -> None:
    """Rollover `available` accounts for direct envelope_id transactions."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    env = await _make_envelope(db_session, user.id, "Savings", rollover=True)
    account = await _make_account(db_session, user.id)

    await _make_allocation(db_session, env.id, "2026-01", budgeted=10000)
    await _make_allocation(db_session, env.id, "2026-02", budgeted=5000)

    txn1 = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 1, 15),
        amount=-3000,
        status="real",
        envelope_id=env.id,
    )
    txn2 = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 2, 10),
        amount=-2000,
        status="real",
        envelope_id=env.id,
    )
    db_session.add_all([txn1, txn2])
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-02", user.id)

    # cumulative budgeted = 15000, cumulative activity = -5000
    assert view.envelopes[0].available == 10000
