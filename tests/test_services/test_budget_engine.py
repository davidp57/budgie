"""Tests for the budget engine service (Phase 5).

Tests envelope calculations: budgeted, activity, available,
and the to_be_budgeted month aggregate.

TDD — tests written before implementation.
"""

import datetime

import pytest
from budgie.models.account import Account
from budgie.models.budget import BudgetAllocation
from budgie.models.category import Category, CategoryGroup
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
    db: AsyncSession, user_id: int, name: str = "Food"
) -> tuple[Category, CategoryGroup]:
    """Create a category group + category scoped to user."""
    group = CategoryGroup(user_id=user_id, name="Expenses", sort_order=0)
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
    is_virtual: bool = False,
) -> Transaction:
    """Create and persist a test transaction."""
    txn = Transaction(
        account_id=account_id,
        date=date,
        amount=amount,
        category_id=category_id,
        is_virtual=is_virtual,
    )
    db.add(txn)
    await db.flush()
    return txn


async def _make_allocation(
    db: AsyncSession, category_id: int, month: str, budgeted: int
) -> BudgetAllocation:
    """Create and persist a budget allocation."""
    alloc = BudgetAllocation(category_id=category_id, month=month, budgeted=budgeted)
    db.add(alloc)
    await db.flush()
    return alloc


# ── Tests: envelope.budgeted ─────────────────────────────────────


async def test_budgeted_from_allocation(db_session: AsyncSession) -> None:
    """Envelope budgeted = BudgetAllocation.budgeted for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    await _make_allocation(db_session, cat.id, "2026-01", budgeted=15000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 1
    envelope = view.envelopes[0]
    assert envelope.category_id == cat.id
    assert envelope.budgeted == 15000


async def test_budgeted_zero_when_no_allocation(db_session: AsyncSession) -> None:
    """Envelope budgeted = 0 if no BudgetAllocation exists for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 1
    assert view.envelopes[0].budgeted == 0


async def test_all_categories_appear_even_without_allocation(
    db_session: AsyncSession,
) -> None:
    """All user categories appear in envelopes, regardless of allocations."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id, name="Food")
    await _make_category(db_session, user.id, name="Transport")

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert len(view.envelopes) == 2


# ── Tests: envelope.activity ─────────────────────────────────────


async def test_activity_sums_transactions_for_month(db_session: AsyncSession) -> None:
    """Activity = sum of real transactions for the month in that category."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, name="Groceries")
    account = await _make_account(db_session, user.id)

    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 10),
        amount=-3000,
        category_id=cat.id,
    )
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 20),
        amount=-2000,
        category_id=cat.id,
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    envelope = view.envelopes[0]
    assert envelope.activity == -5000  # sum of two expenses


async def test_activity_includes_virtual_transactions(db_session: AsyncSession) -> None:
    """Virtual transactions count toward envelope activity."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id, name="Rent")
    account = await _make_account(db_session, user.id)

    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 1),
        amount=-80000,
        category_id=cat.id,
        is_virtual=True,
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == -80000


async def test_activity_zero_when_no_transactions(db_session: AsyncSession) -> None:
    """Activity = 0 when there are no transactions for the month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == 0


async def test_activity_excludes_other_months(db_session: AsyncSession) -> None:
    """Transactions from other months do not count in this month's activity."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    account = await _make_account(db_session, user.id)

    # Transaction in February — should NOT appear in January activity
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 2, 5),
        amount=-5000,
        category_id=cat.id,
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].activity == 0


# ── Tests: envelope.available ────────────────────────────────────


async def test_available_equals_budgeted_minus_activity(
    db_session: AsyncSession,
) -> None:
    """Available = budgeted - activity for a single month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    account = await _make_account(db_session, user.id)

    await _make_allocation(db_session, cat.id, "2026-01", budgeted=10000)
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 15),
        amount=-3000,
        category_id=cat.id,
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].available == 7000  # 10000 - 3000


async def test_available_is_cumulative_across_months(db_session: AsyncSession) -> None:
    """Available = Σ(budgeted) - Σ(activity) over all months up to current."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    account = await _make_account(db_session, user.id)

    # January: budget 100€, spend 30€ → leftover 70€
    await _make_allocation(db_session, cat.id, "2026-01", budgeted=10000)
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 10),
        amount=-3000,
        category_id=cat.id,
    )

    # February: budget 50€, spend 20€ → leftover 30€
    await _make_allocation(db_session, cat.id, "2026-02", budgeted=5000)
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 2, 10),
        amount=-2000,
        category_id=cat.id,
    )

    view = await get_month_budget_view(db_session, "2026-02", user.id)

    # available = (10000 + 5000) - (3000 + 2000) = 10000
    assert view.envelopes[0].available == 10000


async def test_available_future_months_not_counted(db_session: AsyncSession) -> None:
    """Allocations/transactions from future months do not affect current available."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)

    await _make_allocation(db_session, cat.id, "2026-01", budgeted=5000)
    # March allocation should NOT be counted when viewing January
    await _make_allocation(db_session, cat.id, "2026-03", budgeted=9999)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes[0].available == 5000


# ── Tests: to_be_budgeted ────────────────────────────────────────


async def test_to_be_budgeted_income_minus_total_budgeted(
    db_session: AsyncSession,
) -> None:
    """to_be_budgeted = sum(positive uncategorized) - sum(budgeted allocations)."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    cat, _ = await _make_category(db_session, user.id)
    account = await _make_account(db_session, user.id)

    # Income (positive, no category)
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2026, 1, 1),
        amount=200000,  # 2000€ income
        category_id=None,
    )
    await _make_allocation(db_session, cat.id, "2026-01", budgeted=150000)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 50000  # 200000 - 150000


async def test_to_be_budgeted_zero_income_no_budget(db_session: AsyncSession) -> None:
    """to_be_budgeted = 0 when no income and no budget."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 0


async def test_to_be_budgeted_negative_expenses_not_counted_as_income(
    db_session: AsyncSession,
) -> None:
    """Negative uncategorized transactions do not count as income."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id)
    acc = await _make_account(db_session, user.id)

    # Negative uncategorized transaction (e.g., bank fees) — NOT income
    await _make_transaction(
        db_session,
        acc.id,
        datetime.date(2026, 1, 5),
        amount=-1000,
        category_id=None,
    )

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.to_be_budgeted == 0


# ── Tests: user scoping ──────────────────────────────────────────


async def test_envelopes_scoped_to_user(db_session: AsyncSession) -> None:
    """Categories from another user do not appear in the budget view."""
    from budgie.services.budget import get_month_budget_view

    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    await _make_category(db_session, alice.id, "Alice Food")
    await _make_category(db_session, bob.id, "Bob Transport")

    alice_view = await get_month_budget_view(db_session, "2026-01", alice.id)
    bob_view = await get_month_budget_view(db_session, "2026-01", bob.id)

    assert len(alice_view.envelopes) == 1
    assert alice_view.envelopes[0].category_name == "Alice Food"
    assert len(bob_view.envelopes) == 1
    assert bob_view.envelopes[0].category_name == "Bob Transport"


async def test_activity_scoped_to_user_accounts(db_session: AsyncSession) -> None:
    """Transactions from another user's accounts don't affect activity."""
    from budgie.services.budget import get_month_budget_view

    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")

    # Alice has a category
    cat, _ = await _make_category(db_session, alice.id)
    # Bob has an account that somehow references Alice's category — should not count
    bob_account = await _make_account(db_session, bob.id, "Bob Checking")
    await _make_transaction(
        db_session,
        bob_account.id,
        datetime.date(2026, 1, 10),
        amount=-5000,
        category_id=cat.id,
    )

    alice_view = await get_month_budget_view(db_session, "2026-01", alice.id)

    # Alice's activity should be 0, not -5000 (Bob's transaction)
    assert alice_view.envelopes[0].activity == 0


# ── Tests: month metadata ────────────────────────────────────────


async def test_month_in_response(db_session: AsyncSession) -> None:
    """MonthBudgetResponse.month matches the requested month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)

    view = await get_month_budget_view(db_session, "2026-03", user.id)

    assert view.month == "2026-03"


async def test_empty_view_when_no_categories(db_session: AsyncSession) -> None:
    """Returns empty envelopes list when user has no categories."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    assert view.envelopes == []
    assert view.to_be_budgeted == 0


# ── Tests: envelope metadata ─────────────────────────────────────


async def test_envelope_contains_category_and_group_names(
    db_session: AsyncSession,
) -> None:
    """Envelope includes denormalized category and group names for the UI."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    group = CategoryGroup(user_id=user.id, name="Household", sort_order=0)
    db_session.add(group)
    await db_session.flush()
    cat = Category(group_id=group.id, name="Electricity", sort_order=0)
    db_session.add(cat)
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    envelope = view.envelopes[0]
    assert envelope.category_name == "Electricity"
    assert envelope.group_name == "Household"
    assert envelope.group_id == group.id


async def test_hidden_categories_excluded(db_session: AsyncSession) -> None:
    """Hidden categories are excluded from the budget view."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    group = CategoryGroup(user_id=user.id, name="Old", sort_order=0)
    db_session.add(group)
    await db_session.flush()
    hidden_cat = Category(
        group_id=group.id, name="Deprecated", sort_order=0, hidden=True
    )
    visible_cat = Category(group_id=group.id, name="Active", sort_order=1, hidden=False)
    db_session.add(hidden_cat)
    db_session.add(visible_cat)
    await db_session.flush()

    view = await get_month_budget_view(db_session, "2026-01", user.id)

    names = [e.category_name for e in view.envelopes]
    assert "Active" in names
    assert "Deprecated" not in names


async def test_to_be_budgeted_only_current_month_income(
    db_session: AsyncSession,
) -> None:
    """Income from other months does not affect to_be_budgeted for current month."""
    from budgie.services.budget import get_month_budget_view

    user = await _make_user(db_session)
    await _make_category(db_session, user.id)
    account = await _make_account(db_session, user.id)

    # December income — should NOT be counted in January
    await _make_transaction(
        db_session,
        account.id,
        datetime.date(2025, 12, 31),
        amount=300000,
        category_id=None,
    )

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
