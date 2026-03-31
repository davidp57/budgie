"""Categorization engine — Phase 4.

Implements the two-step categorization logic:

1. Payee lookup  → ``Payee.auto_category_id``  (confidence: **auto**)
2. CategoryRule  → first matching rule by priority desc  (confidence: **rule**)
3. No match      → ``None``                              (confidence: **none**)
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.category_rule import CategoryRule
from budgie.models.payee import Payee
from budgie.schemas.categorizer import CategorizeResult

log = logging.getLogger(__name__)


async def categorize_transaction(
    db: AsyncSession,
    user_id: int,
    payee_name: str | None,
    memo: str | None,
    amount: int | None = None,
) -> CategorizeResult:
    """Categorize a single transaction using payee lookup then rule matching.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user who owns the data.
        payee_name: The payee / merchant name from the bank export.
        memo: Optional free-text memo / description.
        amount: Optional transaction amount in centimes. When provided,
            rules with min_amount / max_amount constraints are filtered
            accordingly. When ``None``, amount range constraints are ignored.

    Returns:
        A :class:`~budgie.schemas.categorizer.CategorizeResult` with the
        matched ``category_id`` and a ``confidence`` label.
    """
    # ------------------------------------------------------------------
    # Step 1: Exact payee match (case-insensitive)
    # ------------------------------------------------------------------
    if payee_name is not None:
        stmt = select(Payee).where(
            Payee.user_id == user_id,
            func.lower(Payee.name) == payee_name.lower(),
        )
        payee = (await db.execute(stmt)).scalar_one_or_none()
        if payee and payee.auto_category_id is not None:
            return CategorizeResult(
                category_id=payee.auto_category_id, confidence="auto"
            )

    # ------------------------------------------------------------------
    # Step 2: CategoryRule pass (highest priority first)
    # ------------------------------------------------------------------
    rules_stmt = (
        select(CategoryRule)
        .where(CategoryRule.user_id == user_id)
        .order_by(CategoryRule.priority.desc())
    )
    rules = (await db.execute(rules_stmt)).scalars().all()

    log.debug(
        "categorize: amount=%r  (%d rules to check)",
        amount,
        len(rules),
    )
    for rule in rules:
        value = payee_name if rule.match_field == "payee" else memo
        if value is None:
            log.debug(
                "  rule %d [%r] → SKIP (value is None for field=%r)",
                rule.id,
                rule.pattern,
                rule.match_field,
            )
            continue
        if not _matches(rule.pattern, rule.match_type, value):
            log.debug(
                "  rule %d [%r] → SKIP (text no match)",
                rule.id,
                rule.pattern,
            )
            continue
        # Sign filter: skip if the transaction sign doesn't match the rule type.
        if rule.transaction_type == "debit" and amount is not None and amount >= 0:
            log.debug(
                "  rule %d [%r] → SKIP (type=debit but amount=%r >= 0)",
                rule.id,
                rule.pattern,
                amount,
            )
            continue
        if rule.transaction_type == "credit" and amount is not None and amount <= 0:
            log.debug(
                "  rule %d [%r] → SKIP (type=credit but amount=%r <= 0)",
                rule.id,
                rule.pattern,
                amount,
            )
            continue
        if not _amount_in_range(amount, rule.min_amount, rule.max_amount):
            log.debug(
                "  rule %d [%r] → SKIP (amount %r not in range [%r, %r])",
                rule.id,
                rule.pattern,
                amount,
                rule.min_amount,
                rule.max_amount,
            )
            continue
        log.debug(
            "  rule %d [%r] → MATCH (category_id=%d)",
            rule.id,
            rule.pattern,
            rule.category_id,
        )
        return CategorizeResult(category_id=rule.category_id, confidence="rule")

    # ------------------------------------------------------------------
    # Step 3: No match
    # ------------------------------------------------------------------
    return CategorizeResult(category_id=None, confidence="none")


def _matches(pattern: str, match_type: str, value: str) -> bool:
    """Test whether *value* matches *pattern* according to *match_type*.

    Args:
        pattern: The pattern string stored in the rule.
        match_type: One of ``"contains"``, ``"exact"``, ``"regex"``.
        value: The transaction field value to test.

    Returns:
        ``True`` if the value matches the pattern.
    """
    if match_type == "contains":
        return pattern.lower() in value.lower()
    if match_type == "exact":
        return pattern.lower() == value.lower()
    if match_type == "regex":
        return re.search(pattern, value, re.IGNORECASE) is not None
    return False


def _amount_in_range(
    amount: int | None,
    min_amount: int | None,
    max_amount: int | None,
) -> bool:
    """Return True if *amount* satisfies the optional [min_amount, max_amount] range.

    Comparison is performed on the **absolute value** of *amount*, so that both
    debit transactions (negative centimes) and credit transactions (positive
    centimes) are handled symmetrically.  Rules always store positive bounds.

    When *amount* is ``None`` the check is skipped (returns ``True``).
    Each bound is independently optional.

    Args:
        amount: Transaction amount in centimes (may be negative for debits).
        min_amount: Inclusive lower bound in absolute centimes, or ``None``.
        max_amount: Inclusive upper bound in absolute centimes, or ``None``.

    Returns:
        ``True`` when ``abs(amount)`` satisfies all active constraints.
    """
    if amount is None:
        return True
    abs_amount = abs(amount)
    return (min_amount is None or abs_amount >= min_amount) and (
        max_amount is None or abs_amount <= max_amount
    )
