"""Category groups CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.category import CategoryGroupCreate, CategoryGroupRead
from budgie.services.category import (
    create_category_group,
    delete_category_group,
    get_category_group,
    get_category_groups,
)

router = APIRouter(prefix="/api/category-groups", tags=["categories"])


@router.get("", response_model=list[CategoryGroupRead])
async def list_category_groups(
    db: DBSession,
    current_user: CurrentUser,
) -> list[CategoryGroupRead]:
    """List all category groups for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of category groups with their categories.
    """
    groups = await get_category_groups(db, current_user.id)
    return [CategoryGroupRead.model_validate(g) for g in groups]


@router.post("", response_model=CategoryGroupRead, status_code=status.HTTP_201_CREATED)
async def create_category_group_endpoint(
    schema: CategoryGroupCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryGroupRead:
    """Create a new category group.

    Args:
        schema: Group creation data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Created category group.
    """
    group = await create_category_group(db, schema, current_user.id)
    return CategoryGroupRead.model_validate(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_group_endpoint(
    group_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a category group.

    Args:
        group_id: CategoryGroup primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if group not found.
    """
    group = await get_category_group(db, group_id, current_user.id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category group not found"
        )
    await delete_category_group(db, group)
