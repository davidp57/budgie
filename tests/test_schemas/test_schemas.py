"""Tests for Pydantic request/response schemas.

Validates that schemas properly serialize, deserialize, and enforce
validation constraints.
"""

import datetime

import pytest
from pydantic import ValidationError

# ── User schemas ─────────────────────────────────────────────────


def test_user_create_valid():
    from budgie.schemas.user import UserCreate

    user = UserCreate(username="alice", password="securepass123")
    assert user.username == "alice"
    assert user.password == "securepass123"


def test_user_create_username_too_short():
    from budgie.schemas.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(username="ab", password="securepass123")


def test_user_create_password_too_short():
    from budgie.schemas.user import UserCreate

    with pytest.raises(ValidationError):
        UserCreate(username="alice", password="short")


def test_user_read():
    from budgie.schemas.user import UserRead

    user = UserRead(id=1, username="alice", created_at=datetime.datetime(2026, 1, 1))
    assert user.id == 1
    assert user.username == "alice"


# ── Account schemas ──────────────────────────────────────────────


def test_account_create_valid():
    from budgie.schemas.account import AccountCreate

    account = AccountCreate(name="Checking", account_type="checking", on_budget=True)
    assert account.name == "Checking"
    assert account.account_type == "checking"


def test_account_create_invalid_type():
    from budgie.schemas.account import AccountCreate

    with pytest.raises(ValidationError):
        AccountCreate(name="My Account", account_type="invalid", on_budget=True)


def test_account_read():
    from budgie.schemas.account import AccountRead

    account = AccountRead(
        id=1,
        user_id=1,
        name="Savings",
        account_type="savings",
        on_budget=True,
        created_at=datetime.datetime(2026, 1, 1),
    )
    assert account.id == 1


def test_account_update_partial():
    from budgie.schemas.account import AccountUpdate

    update = AccountUpdate(name="New Name")
    assert update.name == "New Name"
    assert update.account_type is None
    assert update.on_budget is None


# ── Category schemas ─────────────────────────────────────────────


def test_category_group_create():
    from budgie.schemas.category import CategoryGroupCreate

    group = CategoryGroupCreate(name="Bills", sort_order=1)
    assert group.name == "Bills"


def test_category_group_read_with_categories():
    from budgie.schemas.category import CategoryGroupRead, CategoryRead

    group = CategoryGroupRead(
        id=1,
        user_id=1,
        name="Bills",
        sort_order=1,
        categories=[
            CategoryRead(
                id=1,
                group_id=1,
                name="Electricity",
                sort_order=1,
                hidden=False,
            ),
            CategoryRead(
                id=2,
                group_id=1,
                name="Water",
                sort_order=2,
                hidden=False,
            ),
        ],
    )
    assert len(group.categories) == 2


def test_category_create():
    from budgie.schemas.category import CategoryCreate

    cat = CategoryCreate(name="Electricity", group_id=1, sort_order=1, hidden=False)
    assert cat.name == "Electricity"
    assert cat.group_id == 1


def test_category_create_defaults():
    from budgie.schemas.category import CategoryCreate

    cat = CategoryCreate(name="Water", group_id=1)
    assert cat.sort_order == 0
    assert cat.hidden is False


# ── Payee schemas ────────────────────────────────────────────────


def test_payee_create():
    from budgie.schemas.payee import PayeeCreate

    payee = PayeeCreate(name="Carrefour", auto_category_id=5)
    assert payee.name == "Carrefour"
    assert payee.auto_category_id == 5


def test_payee_create_without_category():
    from budgie.schemas.payee import PayeeCreate

    payee = PayeeCreate(name="Unknown")
    assert payee.auto_category_id is None


def test_payee_read():
    from budgie.schemas.payee import PayeeRead

    payee = PayeeRead(id=1, user_id=1, name="Carrefour", auto_category_id=5)
    assert payee.id == 1


# ── Transaction schemas ──────────────────────────────────────────


def test_transaction_create_valid():
    from budgie.schemas.transaction import TransactionCreate

    txn = TransactionCreate(
        account_id=1,
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        cleared="cleared",
    )
    assert txn.amount == -5050


def test_transaction_create_invalid_cleared():
    from budgie.schemas.transaction import TransactionCreate

    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            date=datetime.date(2026, 1, 15),
            amount=-5050,
            cleared="invalid_status",
        )


def test_transaction_read():
    from budgie.schemas.transaction import TransactionRead

    txn = TransactionRead(
        id=1,
        account_id=1,
        date=datetime.date(2026, 1, 15),
        payee_id=None,
        category_id=None,
        amount=-5050,
        memo=None,
        cleared="uncleared",
        is_virtual=False,
        virtual_linked_id=None,
        import_hash=None,
        created_at=datetime.datetime(2026, 1, 15),
        status="real",
    )
    assert txn.id == 1


def test_transaction_update_partial():
    from budgie.schemas.transaction import TransactionUpdate

    update = TransactionUpdate(category_id=3, cleared="cleared")
    assert update.category_id == 3
    assert update.amount is None


def test_split_transaction_create():
    from budgie.schemas.transaction import SplitTransactionCreate

    split = SplitTransactionCreate(category_id=1, amount=-7000, memo="Food items")
    assert split.amount == -7000


# ── BudgetAllocation schemas ─────────────────────────────────────


def test_budget_allocation_create():
    from budgie.schemas.budget import BudgetLineInput

    line = BudgetLineInput(envelope_id=1, budgeted=15000)
    assert line.budgeted == 15000


def test_budget_allocation_invalid_month_format():
    from budgie.schemas.budget import BudgetLineInput

    # envelope_id is required — omitting it must raise ValidationError
    with pytest.raises(ValidationError):
        BudgetLineInput(budgeted=15000)  # type: ignore[call-arg]


def test_budget_allocation_negative_budget():
    from budgie.schemas.budget import BudgetLineInput

    # Negative budgeted amounts should be rejected
    with pytest.raises(ValidationError):
        BudgetLineInput(envelope_id=1, budgeted=-100)


def test_budget_allocation_read():
    from budgie.schemas.budget import BudgetAllocationRead

    alloc = BudgetAllocationRead(id=1, envelope_id=1, month="2026-01", budgeted=15000)
    assert alloc.id == 1
    assert alloc.envelope_id == 1


# ── CategoryRule schemas ─────────────────────────────────────────


def test_category_rule_create():
    from budgie.schemas.category_rule import CategoryRuleCreate

    rule = CategoryRuleCreate(
        pattern="carrefour",
        match_field="payee",
        match_type="contains",
        category_id=1,
        priority=10,
    )
    assert rule.pattern == "carrefour"


def test_category_rule_invalid_match_field():
    from budgie.schemas.category_rule import CategoryRuleCreate

    with pytest.raises(ValidationError):
        CategoryRuleCreate(
            pattern="test",
            match_field="invalid_field",
            match_type="contains",
            category_id=1,
        )


def test_category_rule_invalid_match_type():
    from budgie.schemas.category_rule import CategoryRuleCreate

    with pytest.raises(ValidationError):
        CategoryRuleCreate(
            pattern="test",
            match_field="payee",
            match_type="invalid_type",
            category_id=1,
        )


def test_category_rule_read():
    from budgie.schemas.category_rule import CategoryRuleRead

    rule = CategoryRuleRead(
        id=1,
        user_id=1,
        pattern="carrefour",
        match_field="payee",
        match_type="contains",
        category_id=1,
        priority=10,
    )
    assert rule.id == 1


# ── Envelope v2 schemas (type, period, target) ───────────────────


def test_envelope_create_with_type():
    from budgie.schemas.envelope import EnvelopeCreate

    env = EnvelopeCreate(name="Jeux", envelope_type="cumulative")
    assert env.envelope_type == "cumulative"


def test_envelope_create_default_type():
    from budgie.schemas.envelope import EnvelopeCreate

    env = EnvelopeCreate(name="Courses")
    assert env.envelope_type == "regular"


def test_envelope_create_reserve_type():
    from budgie.schemas.envelope import EnvelopeCreate

    env = EnvelopeCreate(name="Putes", envelope_type="reserve")
    assert env.envelope_type == "reserve"


def test_envelope_create_invalid_type():
    from budgie.schemas.envelope import EnvelopeCreate

    with pytest.raises(ValidationError):
        EnvelopeCreate(name="Bad", envelope_type="invalid")


def test_envelope_create_with_target():
    from budgie.schemas.envelope import EnvelopeCreate

    env = EnvelopeCreate(
        name="Vacances",
        envelope_type="cumulative",
        target_amount=300000,
        stop_on_target=True,
    )
    assert env.target_amount == 300000
    assert env.stop_on_target is True


def test_envelope_create_period():
    from budgie.schemas.envelope import EnvelopeCreate

    env = EnvelopeCreate(name="Loyer", period="monthly")
    assert env.period == "monthly"


def test_envelope_create_invalid_period():
    from budgie.schemas.envelope import EnvelopeCreate

    with pytest.raises(ValidationError):
        EnvelopeCreate(name="Bad", period="biweekly")


def test_envelope_read_v2_fields():
    from budgie.schemas.envelope import EnvelopeRead

    env = EnvelopeRead(
        id=1,
        name="Vacances",
        rollover=True,
        sort_order=0,
        categories=[],
        envelope_type="cumulative",
        period="monthly",
        target_amount=300000,
        stop_on_target=True,
    )
    assert env.envelope_type == "cumulative"
    assert env.target_amount == 300000


def test_envelope_update_type():
    from budgie.schemas.envelope import EnvelopeUpdate

    update = EnvelopeUpdate(envelope_type="reserve")
    assert update.envelope_type == "reserve"


# ── Transaction v2 schemas (status replaces cleared/is_virtual) ──


def test_transaction_create_v2_status():
    from budgie.schemas.transaction import TransactionCreate

    txn = TransactionCreate(
        account_id=1,
        date=datetime.date(2026, 3, 15),
        amount=-5050,
        status="planned",
    )
    assert txn.status == "planned"


def test_transaction_create_v2_default_status():
    from budgie.schemas.transaction import TransactionCreate

    txn = TransactionCreate(
        account_id=1,
        date=datetime.date(2026, 3, 15),
        amount=-5050,
    )
    assert txn.status == "real"


def test_transaction_create_v2_invalid_status():
    from budgie.schemas.transaction import TransactionCreate

    with pytest.raises(ValidationError):
        TransactionCreate(
            account_id=1,
            date=datetime.date(2026, 3, 15),
            amount=-5050,
            status="invalid",
        )


def test_transaction_read_v2():
    from budgie.schemas.transaction import TransactionRead

    txn = TransactionRead(
        id=1,
        account_id=1,
        date=datetime.date(2026, 3, 15),
        payee_id=None,
        category_id=None,
        amount=-5050,
        memo=None,
        status="real",
        import_hash=None,
        created_at=datetime.datetime(2026, 3, 15),
    )
    assert txn.status == "real"


# ── Account v2 schemas (wallet type) ─────────────────────────────


def test_account_create_wallet():
    from budgie.schemas.account import AccountCreate

    account = AccountCreate(name="Portefeuille", account_type="wallet")
    assert account.account_type == "wallet"


# ── CategoryRule amount range schemas ────────────────────────────


def test_category_rule_amount_range_create():
    """min_amount and max_amount are accepted and stored on CategoryRuleCreate."""
    from budgie.schemas.category_rule import CategoryRuleCreate

    rule = CategoryRuleCreate(
        pattern="shop",
        match_field="payee",
        match_type="contains",
        category_id=1,
        min_amount=500,
        max_amount=5000,
    )
    assert rule.min_amount == 500
    assert rule.max_amount == 5000


def test_category_rule_amount_range_defaults_none():
    """min_amount and max_amount default to None."""
    from budgie.schemas.category_rule import CategoryRuleCreate

    rule = CategoryRuleCreate(
        pattern="shop",
        match_field="payee",
        match_type="contains",
        category_id=1,
    )
    assert rule.min_amount is None
    assert rule.max_amount is None


def test_category_rule_amount_range_min_gt_max_invalid():
    """min_amount > max_amount must raise ValidationError."""
    from budgie.schemas.category_rule import CategoryRuleCreate

    with pytest.raises(ValidationError):
        CategoryRuleCreate(
            pattern="shop",
            match_field="payee",
            match_type="contains",
            category_id=1,
            min_amount=-500,
            max_amount=-5000,
        )
