"""Tests for the categorization engine — Phase 4 (TDD red → green)."""

from __future__ import annotations

from budgie.models.category import Category, CategoryGroup
from budgie.models.category_rule import CategoryRule
from budgie.models.payee import Payee
from budgie.models.user import User
from budgie.schemas.categorizer import CategorizeResult
from budgie.services.auth import hash_password
from budgie.services.categorizer import categorize_transaction
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _make_user(db: AsyncSession, username: str = "alice") -> User:
    """Insert a minimal user row and return it."""
    user = User(username=username, hashed_password=hash_password("pw"))
    db.add(user)
    await db.flush()
    return user


async def _make_category(
    db: AsyncSession, user_id: int, name: str = "Food"
) -> Category:
    """Insert a category group + category and return the category."""
    group = CategoryGroup(user_id=user_id, name=f"Group-{name}", sort_order=0)
    db.add(group)
    await db.flush()
    cat = Category(group_id=group.id, name=name, sort_order=0)
    db.add(cat)
    await db.flush()
    return cat


# ---------------------------------------------------------------------------
# No-match cases
# ---------------------------------------------------------------------------


async def test_no_payee_no_rule_returns_none(db_session: AsyncSession) -> None:
    """Both payee and memo are None → confidence 'none'."""
    user = await _make_user(db_session)
    result = await categorize_transaction(db_session, user.id, None, None)
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_unknown_payee_no_rule_returns_none(db_session: AsyncSession) -> None:
    """Payee not in the DB, no rules → confidence 'none'."""
    user = await _make_user(db_session)
    result = await categorize_transaction(db_session, user.id, "Unknown Shop", None)
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_payee_in_db_without_auto_category_no_rule_returns_none(
    db_session: AsyncSession,
) -> None:
    """Payee exists but has no auto_category_id, no matching rules → 'none'."""
    user = await _make_user(db_session)
    payee = Payee(user_id=user.id, name="Generic Store", auto_category_id=None)
    db_session.add(payee)
    await db_session.flush()
    result = await categorize_transaction(db_session, user.id, "Generic Store", None)
    assert result == CategorizeResult(category_id=None, confidence="none")


# ---------------------------------------------------------------------------
# Payee auto-category
# ---------------------------------------------------------------------------


async def test_payee_match_returns_auto_category(db_session: AsyncSession) -> None:
    """Known payee with auto_category_id → confidence 'auto'."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Groceries")
    payee = Payee(user_id=user.id, name="Carrefour", auto_category_id=cat.id)
    db_session.add(payee)
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "Carrefour", None)
    assert result == CategorizeResult(category_id=cat.id, confidence="auto")


async def test_payee_match_is_case_insensitive(db_session: AsyncSession) -> None:
    """Payee lookup is case-insensitive."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Transport")
    payee = Payee(user_id=user.id, name="SNCF", auto_category_id=cat.id)
    db_session.add(payee)
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "sncf", None)
    assert result == CategorizeResult(category_id=cat.id, confidence="auto")


async def test_payee_scoped_to_user(db_session: AsyncSession) -> None:
    """A payee belonging to another user is not matched."""
    alice = await _make_user(db_session, "alice")
    bob = await _make_user(db_session, "bob")
    cat = await _make_category(db_session, alice.id, "Alice-cat")
    payee = Payee(user_id=alice.id, name="Amazon", auto_category_id=cat.id)
    db_session.add(payee)
    await db_session.flush()

    result = await categorize_transaction(db_session, bob.id, "Amazon", None)
    assert result == CategorizeResult(category_id=None, confidence="none")


# ---------------------------------------------------------------------------
# CategoryRule — match_type
# ---------------------------------------------------------------------------


async def test_rule_contains_payee(db_session: AsyncSession) -> None:
    """Rule with match_type='contains', match_field='payee' matches substring."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Online")
    rule = CategoryRule(
        user_id=user.id,
        pattern="amaz",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "Amazon FR", None)
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_contains_is_case_insensitive(db_session: AsyncSession) -> None:
    """Rule 'contains' matching is case-insensitive."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Online")
    rule = CategoryRule(
        user_id=user.id,
        pattern="AMAZON",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "amazon fr", None)
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_exact_payee(db_session: AsyncSession) -> None:
    """Rule with match_type='exact' requires full string equality (case-insensitive)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Fuel")
    rule = CategoryRule(
        user_id=user.id,
        pattern="Total Energie",
        match_field="payee",
        match_type="exact",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    assert await categorize_transaction(
        db_session, user.id, "total energie", None
    ) == CategorizeResult(category_id=cat.id, confidence="rule")
    assert await categorize_transaction(
        db_session, user.id, "Total Energie Extra", None
    ) == CategorizeResult(category_id=None, confidence="none")


async def test_rule_regex_payee(db_session: AsyncSession) -> None:
    """Rule with match_type='regex' applies a regular expression."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Utilities")
    rule = CategoryRule(
        user_id=user.id,
        pattern=r"EDF\s+\d+",
        match_field="payee",
        match_type="regex",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    assert await categorize_transaction(
        db_session, user.id, "EDF 12345", None
    ) == CategorizeResult(category_id=cat.id, confidence="rule")
    assert await categorize_transaction(
        db_session, user.id, "EDF no-digits", None
    ) == CategorizeResult(category_id=None, confidence="none")


async def test_rule_memo_field(db_session: AsyncSession) -> None:
    """Rule with match_field='memo' matches against the memo string."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Rent")
    rule = CategoryRule(
        user_id=user.id,
        pattern="loyer",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    # Matches memo
    assert await categorize_transaction(
        db_session, user.id, "VIREMENT", "paiement loyer mars"
    ) == CategorizeResult(category_id=cat.id, confidence="rule")
    # Payee doesn't contain 'loyer', memo is None → no match
    assert await categorize_transaction(
        db_session, user.id, "loyer", None
    ) == CategorizeResult(category_id=None, confidence="none")


# ---------------------------------------------------------------------------
# Priority & precedence
# ---------------------------------------------------------------------------


async def test_rule_higher_priority_wins(db_session: AsyncSession) -> None:
    """When multiple rules match, the one with the highest priority is used."""
    user = await _make_user(db_session)
    cat_low = await _make_category(db_session, user.id, "Generic")
    cat_high = await _make_category(db_session, user.id, "Streaming")
    rule_low = CategoryRule(
        user_id=user.id,
        pattern="netflix",
        match_field="payee",
        match_type="contains",
        category_id=cat_low.id,
        priority=0,
    )
    rule_high = CategoryRule(
        user_id=user.id,
        pattern="netflix",
        match_field="payee",
        match_type="contains",
        category_id=cat_high.id,
        priority=10,
    )
    db_session.add_all([rule_low, rule_high])
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "NETFLIX", None)
    assert result == CategorizeResult(category_id=cat_high.id, confidence="rule")


async def test_payee_auto_category_takes_precedence_over_rule(
    db_session: AsyncSession,
) -> None:
    """Payee auto-category wins over a matching rule (step 1 before step 2)."""
    user = await _make_user(db_session)
    cat_payee = await _make_category(db_session, user.id, "Payee-cat")
    cat_rule = await _make_category(db_session, user.id, "Rule-cat")

    payee = Payee(user_id=user.id, name="Monoprix", auto_category_id=cat_payee.id)
    rule = CategoryRule(
        user_id=user.id,
        pattern="monoprix",
        match_field="payee",
        match_type="contains",
        category_id=cat_rule.id,
        priority=100,
    )
    db_session.add_all([payee, rule])
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "Monoprix", None)
    assert result == CategorizeResult(category_id=cat_payee.id, confidence="auto")


async def test_payee_without_auto_category_falls_through_to_rule(
    db_session: AsyncSession,
) -> None:
    """Payee found but auto_category_id=None → engine falls through to rules."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Supermarket")
    payee = Payee(user_id=user.id, name="Lidl", auto_category_id=None)
    rule = CategoryRule(
        user_id=user.id,
        pattern="lidl",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add_all([payee, rule])
    await db_session.flush()

    result = await categorize_transaction(db_session, user.id, "Lidl", None)
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


# ---------------------------------------------------------------------------
# Amount range filtering
# ---------------------------------------------------------------------------


async def _make_rule(
    db: AsyncSession,
    user_id: int,
    category_id: int,
    *,
    min_amount: int | None = None,
    max_amount: int | None = None,
) -> CategoryRule:
    """Insert a simple 'contains/payee' rule with optional amount range."""
    rule = CategoryRule(
        user_id=user_id,
        pattern="shop",
        match_field="payee",
        match_type="contains",
        category_id=category_id,
        priority=0,
        min_amount=min_amount,
        max_amount=max_amount,
    )
    db.add(rule)
    await db.flush()
    return rule


async def test_rule_amount_range_match(db_session: AsyncSession) -> None:
    """abs(amount) within [min_amount, max_amount] → rule matches (debit and credit)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, min_amount=500, max_amount=5000)

    # Debit: -20 EUR (-2000 ct) → abs=2000, within [500, 5000]
    result = await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-2000
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")
    # Credit: +20 EUR (+2000 ct) → abs=2000, within [500, 5000]
    result = await categorize_transaction(
        db_session, user.id, "my shop", None, amount=2000
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_amount_range_no_match_below_min(db_session: AsyncSession) -> None:
    """abs(amount) < min_amount → rule is skipped."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, min_amount=500, max_amount=5000)

    # -2 EUR (-200 ct) → abs=200 < 500
    result = await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-200
    )
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_rule_amount_range_no_match_above_max(db_session: AsyncSession) -> None:
    """abs(amount) > max_amount → rule is skipped."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, min_amount=500, max_amount=5000)

    # -100 EUR (-10000 ct) → abs=10000 > 5000
    result = await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-10000
    )
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_rule_amount_range_ignored_when_amount_none(
    db_session: AsyncSession,
) -> None:
    """When amount=None, amount range constraints are skipped and text still matches."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, min_amount=500, max_amount=5000)

    result = await categorize_transaction(
        db_session, user.id, "my shop", None, amount=None
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_only_min_amount(db_session: AsyncSession) -> None:
    """Only min_amount set: matches when abs(amount) >= min_amount."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, min_amount=500)

    # -20 EUR → abs=2000 >= 500 → match
    assert await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-2000
    ) == CategorizeResult(category_id=cat.id, confidence="rule")
    # -2 EUR → abs=200 < 500 → no match
    assert await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-200
    ) == CategorizeResult(category_id=None, confidence="none")


async def test_rule_only_max_amount(db_session: AsyncSession) -> None:
    """Only max_amount set: matches when abs(amount) <= max_amount."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id)
    await _make_rule(db_session, user.id, cat.id, max_amount=500)

    # -2 EUR → abs=200 <= 500 → match
    assert await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-200
    ) == CategorizeResult(category_id=cat.id, confidence="rule")
    # -20 EUR → abs=2000 > 500 → no match
    assert await categorize_transaction(
        db_session, user.id, "my shop", None, amount=-2000
    ) == CategorizeResult(category_id=None, confidence="none")


async def test_rule_payee_field_matches_when_payee_name_provided(
    db_session: AsyncSession,
) -> None:
    """A 'payee'-field rule fires when payeeName == bank.label (recco view pattern)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Jeux")
    rule = CategoryRule(
        user_id=user.id,
        pattern="steamgames",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=0,
        max_amount=1000,
    )
    db_session.add(rule)
    await db_session.flush()

    # Mimics the reconciliation view call: bank.label passed as both payee and memo,
    # bank.amount (+419 ct = AVOIR 4.19€) passed as amount.
    bank_label = "AVOIR 23/03/26 STEAMGAMES.COM 42 CB*6338"
    result = await categorize_transaction(
        db_session, user.id, bank_label, bank_label, amount=419
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_payee_field_skipped_when_payee_name_none(
    db_session: AsyncSession,
) -> None:
    """A 'payee'-field rule is skipped when payeeName=None (old recco view bug)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Jeux")
    rule = CategoryRule(
        user_id=user.id,
        pattern="steamgames",
        match_field="payee",
        match_type="contains",
        category_id=cat.id,
        priority=0,
    )
    db_session.add(rule)
    await db_session.flush()

    # Old call: payeeName=None — 'payee' rule cannot fire.
    bank_label = "AVOIR 23/03/26 STEAMGAMES.COM 42 CB*6338"
    result = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=419
    )
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_rule_positive_amount_range_matches_avoir(
    db_session: AsyncSession,
) -> None:
    """Range [0, 1000] (0-10 EUR) matches a positive AVOIR amount of 419 ct."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Jeux")
    rule = CategoryRule(
        user_id=user.id,
        pattern="steamgames",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=0,
        max_amount=1000,
    )
    db_session.add(rule)
    await db_session.flush()

    bank_label = "AVOIR 23/03/26 STEAMGAMES.COM 42 CB*6338"
    # 4.19 € = 419 ct, within [0, 1000]
    result = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=419
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")

    # 15 € = 1500 ct, outside [0, 1000]
    result_outside = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=1500
    )
    assert result_outside == CategorizeResult(category_id=None, confidence="none")


# ---------------------------------------------------------------------------
# transaction_type filter tests
# ---------------------------------------------------------------------------


async def test_rule_transaction_type_debit_matches_negative_amount(
    db_session: AsyncSession,
) -> None:
    """A 'debit' rule fires when amount < 0."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Groceries")
    rule = CategoryRule(
        user_id=user.id,
        pattern="supermarket",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="debit",
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "supermarket", amount=-500
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_transaction_type_debit_skips_positive_amount(
    db_session: AsyncSession,
) -> None:
    """A 'debit' rule is skipped when amount >= 0."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Groceries")
    rule = CategoryRule(
        user_id=user.id,
        pattern="supermarket",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="debit",
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "supermarket", amount=500
    )
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_rule_transaction_type_credit_matches_positive_amount(
    db_session: AsyncSession,
) -> None:
    """A 'credit' rule fires when amount > 0."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Salary")
    rule = CategoryRule(
        user_id=user.id,
        pattern="virement",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="credit",
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "virement salaire", amount=200000
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_transaction_type_credit_skips_negative_amount(
    db_session: AsyncSession,
) -> None:
    """A 'credit' rule is skipped when amount <= 0."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Salary")
    rule = CategoryRule(
        user_id=user.id,
        pattern="virement",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="credit",
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "virement salaire", amount=-200000
    )
    assert result == CategorizeResult(category_id=None, confidence="none")


async def test_rule_transaction_type_any_matches_both_signs(
    db_session: AsyncSession,
) -> None:
    """An 'any' rule fires for both positive and negative amounts."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Transfer")
    rule = CategoryRule(
        user_id=user.id,
        pattern="transfer",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="any",
    )
    db_session.add(rule)
    await db_session.flush()

    result_neg = await categorize_transaction(
        db_session, user.id, None, "transfer", amount=-1000
    )
    assert result_neg == CategorizeResult(category_id=cat.id, confidence="rule")

    result_pos = await categorize_transaction(
        db_session, user.id, None, "transfer", amount=1000
    )
    assert result_pos == CategorizeResult(category_id=cat.id, confidence="rule")


# ---------------------------------------------------------------------------
# Amount boundary condition tests
# ---------------------------------------------------------------------------


async def test_rule_amount_boundary_at_min(
    db_session: AsyncSession,
) -> None:
    """A rule matches when amount equals min_amount exactly (boundary inclusive)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Coffee")
    rule = CategoryRule(
        user_id=user.id,
        pattern="cafe",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=100,
        max_amount=500,
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "cafe de flore", amount=100
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_amount_boundary_at_max(
    db_session: AsyncSession,
) -> None:
    """A rule matches when amount equals max_amount exactly (boundary inclusive)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Coffee")
    rule = CategoryRule(
        user_id=user.id,
        pattern="cafe",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=100,
        max_amount=500,
    )
    db_session.add(rule)
    await db_session.flush()

    result = await categorize_transaction(
        db_session, user.id, None, "cafe de flore", amount=500
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_negative_amount_uses_absolute_value(
    db_session: AsyncSession,
) -> None:
    """Amount range is compared against the absolute value of the transaction amount."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Groceries")
    rule = CategoryRule(
        user_id=user.id,
        pattern="lidl",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=0,
        max_amount=5000,
    )
    db_session.add(rule)
    await db_session.flush()

    # -3000 ct → absolute value 3000, inside [0, 5000]
    result = await categorize_transaction(
        db_session, user.id, None, "lidl", amount=-3000
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")


async def test_rule_positive_range_matches_debit_amount(
    db_session: AsyncSession,
) -> None:
    """Range [0, 1000] matches a negative debit amount (abs(-419) = 419)."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Courses")
    rule = CategoryRule(
        user_id=user.id,
        pattern="supermarche",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        min_amount=0,
        max_amount=1000,
    )
    db_session.add(rule)
    await db_session.flush()

    bank_label = "VIR PAIEMENT CB SUPERMARCHE"
    # Debit: -4.19 EUR = -419 ct  →  abs = 419, within [0, 1000]
    result = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=-419
    )
    assert result == CategorizeResult(category_id=cat.id, confidence="rule")

    # Debit: -15 EUR = -1500 ct  →  abs = 1500, outside [0, 1000]
    result_outside = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=-1500
    )
    assert result_outside == CategorizeResult(category_id=None, confidence="none")


async def test_rule_debit_type_skips_credit(
    db_session: AsyncSession,
) -> None:
    """transaction_type='debit' rule does not fire for positive (credit) amounts."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Courses")
    rule = CategoryRule(
        user_id=user.id,
        pattern="supermarche",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="debit",
        min_amount=0,
        max_amount=1000,
    )
    db_session.add(rule)
    await db_session.flush()

    bank_label = "VIR PAIEMENT CB SUPERMARCHE"
    # Debit -419 ct  →  sign matches, abs 419 in range  →  match
    result_debit = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=-419
    )
    assert result_debit == CategorizeResult(category_id=cat.id, confidence="rule")

    # Credit +419 ct (e.g. a refund)  →  sign does NOT match  →  skip
    result_credit = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=419
    )
    assert result_credit == CategorizeResult(category_id=None, confidence="none")


async def test_rule_credit_type_skips_debit(
    db_session: AsyncSession,
) -> None:
    """transaction_type='credit' rule does not fire for negative (debit) amounts."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Remboursements")
    rule = CategoryRule(
        user_id=user.id,
        pattern="remboursement",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="credit",
        min_amount=0,
        max_amount=5000,
    )
    db_session.add(rule)
    await db_session.flush()

    bank_label = "REMBOURSEMENT ASSURANCE"
    # Credit +200 ct  →  sign matches  →  match
    result_credit = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=200
    )
    assert result_credit == CategorizeResult(category_id=cat.id, confidence="rule")

    # Debit -200 ct  →  sign does NOT match  →  skip
    result_debit = await categorize_transaction(
        db_session, user.id, None, bank_label, amount=-200
    )
    assert result_debit == CategorizeResult(category_id=None, confidence="none")


async def test_rule_any_type_matches_both_signs(
    db_session: AsyncSession,
) -> None:
    """transaction_type='any' (default) matches both debits and credits."""
    user = await _make_user(db_session)
    cat = await _make_category(db_session, user.id, "Divers")
    rule = CategoryRule(
        user_id=user.id,
        pattern="netflix",
        match_field="memo",
        match_type="contains",
        category_id=cat.id,
        priority=0,
        transaction_type="any",
    )
    db_session.add(rule)
    await db_session.flush()

    for amount in (-1990, 1990):
        result = await categorize_transaction(
            db_session, user.id, None, "NETFLIX COM", amount=amount
        )
        assert result == CategorizeResult(category_id=cat.id, confidence="rule")
