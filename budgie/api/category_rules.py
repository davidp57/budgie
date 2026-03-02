"""CategoryRule CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.category_rule import (
    CategoryRuleCreate,
    CategoryRuleRead,
    CategoryRuleUpdate,
)
from budgie.services.category_rule import (
    create_rule,
    delete_rule,
    get_rule,
    get_rules,
    update_rule,
)

router = APIRouter(prefix="/api/category-rules", tags=["category-rules"])


@router.get("", response_model=list[CategoryRuleRead])
async def list_rules(
    db: DBSession,
    current_user: CurrentUser,
) -> list[CategoryRuleRead]:
    """List all categorization rules for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of CategoryRule data, ordered by descending priority.
    """
    rules = await get_rules(db, current_user.id)
    return [CategoryRuleRead.model_validate(r) for r in rules]


@router.post("", response_model=CategoryRuleRead, status_code=status.HTTP_201_CREATED)
async def create_rule_endpoint(
    schema: CategoryRuleCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryRuleRead:
    """Create a new categorization rule.

    Args:
        schema: Rule creation data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Created CategoryRule data.
    """
    rule = await create_rule(db, schema, current_user.id)
    return CategoryRuleRead.model_validate(rule)


@router.get("/{rule_id}", response_model=CategoryRuleRead)
async def get_rule_endpoint(
    rule_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryRuleRead:
    """Fetch a single categorization rule.

    Args:
        rule_id: Rule primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        CategoryRule data.

    Raises:
        HTTPException: 404 if the rule does not exist or belongs to another user.
    """
    rule = await get_rule(db, rule_id, current_user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    return CategoryRuleRead.model_validate(rule)


@router.put("/{rule_id}", response_model=CategoryRuleRead)
async def update_rule_endpoint(
    rule_id: int,
    schema: CategoryRuleUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryRuleRead:
    """Partially update a categorization rule.

    Args:
        rule_id: Rule primary key.
        schema: Partial update data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Updated CategoryRule data.

    Raises:
        HTTPException: 404 if the rule does not exist or belongs to another user.
    """
    rule = await get_rule(db, rule_id, current_user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    updated = await update_rule(db, rule, schema)
    return CategoryRuleRead.model_validate(updated)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_endpoint(
    rule_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a categorization rule.

    Args:
        rule_id: Rule primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if the rule does not exist or belongs to another user.
    """
    rule = await get_rule(db, rule_id, current_user.id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    await delete_rule(db, rule)
