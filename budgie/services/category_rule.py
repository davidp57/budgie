"""CategoryRule CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.category_rule import CategoryRule
from budgie.schemas.category_rule import CategoryRuleCreate, CategoryRuleUpdate


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
    """
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
    """
    for field, value in schema.model_dump(exclude_unset=True).items():
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
