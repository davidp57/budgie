"""Tests for SQLAlchemy ORM models.

Verifies that all ORM models can be created, persisted, and queried
correctly, including relationships, constraints, and defaults.
"""

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# ── User model tests ──────────────────────────────────────────────


async def test_create_user(db_session: AsyncSession):
    from budgie.models.user import User

    user = User(username="alice", hashed_password="fakehash123")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.username == "alice"
    assert user.hashed_password == "fakehash123"
    assert user.created_at is not None


async def test_user_username_unique(db_session: AsyncSession):
    from budgie.models.user import User

    db_session.add(User(username="bob", hashed_password="hash1"))
    await db_session.commit()

    db_session.add(User(username="bob", hashed_password="hash2"))
    with pytest.raises(IntegrityError):
        await db_session.commit()


# ── Account model tests ──────────────────────────────────────────


async def test_create_account(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id,
        name="Checking",
        account_type="checking",
        on_budget=True,
    )
    db_session.add(account)
    await db_session.commit()
    await db_session.refresh(account)

    assert account.id is not None
    assert account.name == "Checking"
    assert account.account_type == "checking"
    assert account.on_budget is True
    assert account.user_id == user.id


async def test_account_user_relationship(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Savings", account_type="savings", on_budget=True
    )
    db_session.add(account)
    await db_session.commit()

    result = await db_session.execute(select(Account).where(Account.user_id == user.id))
    accounts = result.scalars().all()
    assert len(accounts) == 1
    assert accounts[0].name == "Savings"


# ── CategoryGroup & Category tests ───────────────────────────────


async def test_create_category_group_with_categories(db_session: AsyncSession):
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Bills", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Electricity", sort_order=1, hidden=False)
    db_session.add(cat)
    await db_session.commit()
    await db_session.refresh(cat)

    assert cat.id is not None
    assert cat.name == "Electricity"
    assert cat.group_id == group.id
    assert cat.hidden is False


async def test_category_group_relationship(db_session: AsyncSession):
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Bills", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    db_session.add(Category(group_id=group.id, name="Water", sort_order=1))
    db_session.add(Category(group_id=group.id, name="Gas", sort_order=2))
    await db_session.commit()

    result = await db_session.execute(
        select(Category).where(Category.group_id == group.id)
    )
    categories = result.scalars().all()
    assert len(categories) == 2


# ── Payee model tests ────────────────────────────────────────────


async def test_create_payee(db_session: AsyncSession):
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.payee import Payee
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Food", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Groceries", sort_order=1)
    db_session.add(cat)
    await db_session.commit()

    payee = Payee(user_id=user.id, name="Carrefour", auto_category_id=cat.id)
    db_session.add(payee)
    await db_session.commit()
    await db_session.refresh(payee)

    assert payee.id is not None
    assert payee.name == "Carrefour"
    assert payee.auto_category_id == cat.id


async def test_create_payee_without_auto_category(db_session: AsyncSession):
    from budgie.models.payee import Payee
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    payee = Payee(user_id=user.id, name="Unknown Shop")
    db_session.add(payee)
    await db_session.commit()
    await db_session.refresh(payee)

    assert payee.auto_category_id is None


# ── Transaction model tests ──────────────────────────────────────


async def test_create_transaction(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.payee import Payee
    from budgie.models.transaction import Transaction
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    group = CategoryGroup(user_id=user.id, name="Food", sort_order=1)
    db_session.add_all([account, group])
    await db_session.commit()

    cat = Category(group_id=group.id, name="Groceries", sort_order=1)
    payee = Payee(user_id=user.id, name="Carrefour")
    db_session.add_all([cat, payee])
    await db_session.commit()

    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 1, 15),
        payee_id=payee.id,
        category_id=cat.id,
        amount=-5050,  # -50.50€ in centimes
        memo="Weekly groceries",
        cleared="cleared",
        is_virtual=False,
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    assert txn.id is not None
    assert txn.amount == -5050
    assert txn.cleared == "cleared"
    assert txn.is_virtual is False
    assert txn.import_hash is None
    assert txn.virtual_linked_id is None


async def test_transaction_import_hash_unique(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.transaction import Transaction
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    db_session.add(account)
    await db_session.commit()

    txn1 = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 1, 15),
        amount=-1000,
        cleared="uncleared",
        import_hash="abc123",
    )
    db_session.add(txn1)
    await db_session.commit()

    txn2 = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 1, 16),
        amount=-2000,
        cleared="uncleared",
        import_hash="abc123",
    )
    db_session.add(txn2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


async def test_transaction_defaults(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.transaction import Transaction
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    db_session.add(account)
    await db_session.commit()

    txn = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 2, 1),
        amount=-500,
        cleared="uncleared",
    )
    db_session.add(txn)
    await db_session.commit()
    await db_session.refresh(txn)

    assert txn.is_virtual is False
    assert txn.created_at is not None


# ── SplitTransaction tests ───────────────────────────────────────


async def test_create_split_transaction(db_session: AsyncSession):
    from budgie.models.account import Account
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.transaction import SplitTransaction, Transaction
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    group = CategoryGroup(user_id=user.id, name="Food", sort_order=1)
    db_session.add_all([account, group])
    await db_session.commit()

    cat1 = Category(group_id=group.id, name="Groceries", sort_order=1)
    cat2 = Category(group_id=group.id, name="Household", sort_order=2)
    db_session.add_all([cat1, cat2])
    await db_session.commit()

    parent = Transaction(
        account_id=account.id,
        date=datetime.date(2026, 1, 15),
        amount=-10000,  # -100€
        cleared="cleared",
    )
    db_session.add(parent)
    await db_session.commit()

    split1 = SplitTransaction(
        parent_id=parent.id, category_id=cat1.id, amount=-7000, memo="Food items"
    )
    split2 = SplitTransaction(
        parent_id=parent.id, category_id=cat2.id, amount=-3000, memo="Cleaning"
    )
    db_session.add_all([split1, split2])
    await db_session.commit()

    result = await db_session.execute(
        select(SplitTransaction).where(SplitTransaction.parent_id == parent.id)
    )
    splits = result.scalars().all()
    assert len(splits) == 2
    assert sum(s.amount for s in splits) == -10000


# ── BudgetAllocation tests ───────────────────────────────────────


async def test_create_budget_allocation(db_session: AsyncSession):
    from budgie.models.budget import BudgetAllocation
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Bills", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Electricity", sort_order=1)
    db_session.add(cat)
    await db_session.commit()

    alloc = BudgetAllocation(
        category_id=cat.id,
        month="2026-01",
        budgeted=15000,  # 150€
    )
    db_session.add(alloc)
    await db_session.commit()
    await db_session.refresh(alloc)

    assert alloc.id is not None
    assert alloc.budgeted == 15000
    assert alloc.month == "2026-01"


async def test_budget_allocation_unique_category_month(db_session: AsyncSession):
    from budgie.models.budget import BudgetAllocation
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Bills", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Electricity", sort_order=1)
    db_session.add(cat)
    await db_session.commit()

    alloc1 = BudgetAllocation(category_id=cat.id, month="2026-01", budgeted=15000)
    db_session.add(alloc1)
    await db_session.commit()

    alloc2 = BudgetAllocation(category_id=cat.id, month="2026-01", budgeted=20000)
    db_session.add(alloc2)
    with pytest.raises(IntegrityError):
        await db_session.commit()


# ── CategoryRule tests ────────────────────────────────────────────


async def test_create_category_rule(db_session: AsyncSession):
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.category_rule import CategoryRule
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Food", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Groceries", sort_order=1)
    db_session.add(cat)
    await db_session.commit()

    rule = CategoryRule(
        user_id=user.id,
        pattern="carrefour",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=10,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)

    assert rule.id is not None
    assert rule.pattern == "carrefour"
    assert rule.match_field == "payee"
    assert rule.match_type == "contains"
    assert rule.priority == 10


async def test_category_rules_ordered_by_priority(db_session: AsyncSession):
    from budgie.models.category import Category, CategoryGroup
    from budgie.models.category_rule import CategoryRule
    from budgie.models.user import User

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    group = CategoryGroup(user_id=user.id, name="Food", sort_order=1)
    db_session.add(group)
    await db_session.commit()

    cat = Category(group_id=group.id, name="Groceries", sort_order=1)
    db_session.add(cat)
    await db_session.commit()

    rule_low = CategoryRule(
        user_id=user.id,
        pattern="food",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=1,
    )
    rule_high = CategoryRule(
        user_id=user.id,
        pattern="carrefour",
        match_field="payee",
        match_type="exact",
        category_id=cat.id,
        priority=100,
    )
    db_session.add_all([rule_low, rule_high])
    await db_session.commit()

    result = await db_session.execute(
        select(CategoryRule)
        .where(CategoryRule.user_id == user.id)
        .order_by(CategoryRule.priority.desc())
    )
    rules = result.scalars().all()
    assert rules[0].priority == 100
    assert rules[1].priority == 1
