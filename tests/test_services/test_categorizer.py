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
