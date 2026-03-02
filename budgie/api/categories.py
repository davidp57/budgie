"""Categories CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from budgie.services.category import (
    create_category,
    delete_category,
    get_category,
    get_category_group,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category_endpoint(
    schema: CategoryCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryRead:
    """Create a new category inside a category group.

    Args:
        schema: Category creation data (includes group_id).
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Created category data.

    Raises:
        HTTPException: 404 if the group is not found or not owned by user.
    """
    group = await get_category_group(db, schema.group_id, current_user.id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category group not found",
        )
    category = await create_category(db, schema)
    return CategoryRead.model_validate(category)


@router.put("/{category_id}", response_model=CategoryRead)
async def update_category_endpoint(
    category_id: int,
    schema: CategoryUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> CategoryRead:
    """Partially update a category.

    Args:
        category_id: Category primary key.
        schema: Partial update data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Updated category data.

    Raises:
        HTTPException: 404 if category not found.
    """
    category = await get_category(db, category_id, current_user.id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    updated = await update_category(db, category, schema)
    return CategoryRead.model_validate(updated)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category_endpoint(
    category_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a category.

    Args:
        category_id: Category primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if category not found.
    """
    category = await get_category(db, category_id, current_user.id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    await delete_category(db, category)
