"""CategoryRule CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.category_rule import CategoryRule
from budgie.schemas.category_rule import (
    CategoryRuleCreate,
    CategoryRuleUpdate,
    check_rule_pattern,
)
from budgie.services.ownership import ensure_references_owned

# Columns that are NOT NULL in the database: an explicit ``null`` in a partial
# update must be rejected rather than written.
_REQUIRED_FIELDS = (
    "pattern",
    "match_field",
    "match_type",
    "category_id",
    "priority",
    "transaction_type",
)


async def get_rules(db: AsyncSession, user_id: int) -> list[CategoryRule]:
    """Return all rules for a user, ordered by descending priority.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of CategoryRule instances.
    """
    result = await db.execute(
        select(CategoryRule)
        .where(CategoryRule.user_id == user_id)
        .order_by(CategoryRule.priority.desc())
    )
    return list(result.scalars().all())


async def get_rule(db: AsyncSession, rule_id: int, user_id: int) -> CategoryRule | None:
    """Fetch a single rule scoped to the user.

    Args:
        db: Async database session.
        rule_id: CategoryRule primary key.
        user_id: Owner user ID.

    Returns:
        CategoryRule if found, None otherwise.
    """
    result = await db.execute(
        select(CategoryRule).where(
            CategoryRule.id == rule_id, CategoryRule.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def create_rule(
    db: AsyncSession, schema: CategoryRuleCreate, user_id: int
) -> CategoryRule:
    """Create a new categorization rule.

    Args:
        db: Async database session.
        schema: Validated rule creation schema.
        user_id: Owner user ID.

    Returns:
        Newly created CategoryRule instance.

    Raises:
        ForeignReferenceError: If the category does not belong to the user.
    """
    await ensure_references_owned(db, user_id, category_id=schema.category_id)
    rule = CategoryRule(
        user_id=user_id,
        pattern=schema.pattern,
        match_field=schema.match_field,
        match_type=schema.match_type,
        category_id=schema.category_id,
        priority=schema.priority,
        transaction_type=schema.transaction_type,
        min_amount=schema.min_amount,
        max_amount=schema.max_amount,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession, rule: CategoryRule, schema: CategoryRuleUpdate
) -> CategoryRule:
    """Partially update a categorization rule.

    Args:
        db: Async database session.
        rule: Existing CategoryRule instance.
        schema: Partial update schema.

    Returns:
        Updated CategoryRule instance.

    Raises:
        ValueError: If the merged rule is invalid (null required field,
            bad or ReDoS-prone regex, inverted amount range).
        ForeignReferenceError: If the new category does not belong to the
            rule's owner.
    """
    changes = schema.model_dump(exclude_unset=True)
    for field in _REQUIRED_FIELDS:
        if field in changes and changes[field] is None:
            raise ValueError(f"{field} cannot be null")

    # Validate the rule as it will be stored, not just the submitted fields:
    # a partial update may switch an existing pattern to regex, or change the
    # pattern of a rule that already is one.
    pattern = changes.get("pattern", rule.pattern)
    match_type = changes.get("match_type", rule.match_type)
    check_rule_pattern(pattern, match_type)
    min_amount = changes.get("min_amount", rule.min_amount)
    max_amount = changes.get("max_amount", rule.max_amount)
    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise ValueError("min_amount must be <= max_amount")

    if "category_id" in changes:
        await ensure_references_owned(
            db, rule.user_id, category_id=changes["category_id"]
        )

    for field, value in changes.items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(db: AsyncSession, rule: CategoryRule) -> None:
    """Delete a categorization rule.

    Args:
        db: Async database session.
        rule: CategoryRule instance to delete.
    """
    await db.delete(rule)
    await db.commit()
