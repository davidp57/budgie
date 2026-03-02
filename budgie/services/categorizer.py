"""Categorization engine — Phase 4.

Implements the two-step categorization logic:

1. Payee lookup  → ``Payee.auto_category_id``  (confidence: **auto**)
2. CategoryRule  → first matching rule by priority desc  (confidence: **rule**)
3. No match      → ``None``                              (confidence: **none**)
"""

from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.category_rule import CategoryRule
from budgie.models.payee import Payee
from budgie.schemas.categorizer import CategorizeResult


async def categorize_transaction(
    db: AsyncSession,
    user_id: int,
    payee_name: str | None,
    memo: str | None,
) -> CategorizeResult:
    """Categorize a single transaction using payee lookup then rule matching.

    Args:
        db: Async database session.
        user_id: ID of the authenticated user who owns the data.
        payee_name: The payee / merchant name from the bank export.
        memo: Optional free-text memo / description.

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

    for rule in rules:
        value = payee_name if rule.match_field == "payee" else memo
        if value is None:
            continue
        if _matches(rule.pattern, rule.match_type, value):
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
