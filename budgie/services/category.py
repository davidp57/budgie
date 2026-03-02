"""Category and CategoryGroup CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from budgie.models.category import Category, CategoryGroup
from budgie.schemas.category import (
    CategoryCreate,
    CategoryGroupCreate,
    CategoryUpdate,
)

# ── CategoryGroup ─────────────────────────────────────────────────


async def get_category_groups(db: AsyncSession, user_id: int) -> list[CategoryGroup]:
    """Return all category groups for a user, with their categories.

    Args:
        db: Async database session.
        user_id: Owner user ID.

    Returns:
        List of CategoryGroup instances with categories loaded.
    """
    result = await db.execute(
        select(CategoryGroup)
        .where(CategoryGroup.user_id == user_id)
        .options(selectinload(CategoryGroup.categories))
        .order_by(CategoryGroup.sort_order)
    )
    return list(result.scalars().all())


async def get_category_group(
    db: AsyncSession, group_id: int, user_id: int
) -> CategoryGroup | None:
    """Fetch a single category group, scoped to the user.

    Args:
        db: Async database session.
        group_id: CategoryGroup primary key.
        user_id: Owner user ID.

    Returns:
        CategoryGroup if found, None otherwise.
    """
    result = await db.execute(
        select(CategoryGroup)
        .where(CategoryGroup.id == group_id, CategoryGroup.user_id == user_id)
        .options(selectinload(CategoryGroup.categories))
    )
    return result.scalar_one_or_none()


async def create_category_group(
    db: AsyncSession, schema: CategoryGroupCreate, user_id: int
) -> CategoryGroup:
    """Create a new category group.

    Args:
        db: Async database session.
        schema: Validated group creation schema.
        user_id: Owner user ID.

    Returns:
        Newly created CategoryGroup instance.
    """
    group = CategoryGroup(
        user_id=user_id,
        name=schema.name,
        sort_order=schema.sort_order,
    )
    db.add(group)
    await db.commit()
    await db.refresh(group)
    # Load categories relationship (empty at creation)
    result = await db.execute(
        select(CategoryGroup)
        .where(CategoryGroup.id == group.id)
        .options(selectinload(CategoryGroup.categories))
    )
    return result.scalar_one()


async def delete_category_group(db: AsyncSession, group: CategoryGroup) -> None:
    """Delete a category group and its categories (cascade).

    Args:
        db: Async database session.
        group: CategoryGroup instance to delete.
    """
    await db.delete(group)
    await db.commit()


# ── Category ──────────────────────────────────────────────────────


async def get_category(
    db: AsyncSession, category_id: int, user_id: int
) -> Category | None:
    """Fetch a single category, ensuring it belongs to the user via its group.

    Args:
        db: Async database session.
        category_id: Category primary key.
        user_id: Owner user ID.

    Returns:
        Category if found and owned by user, None otherwise.
    """
    result = await db.execute(
        select(Category)
        .join(CategoryGroup, Category.group_id == CategoryGroup.id)
        .where(Category.id == category_id, CategoryGroup.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, schema: CategoryCreate) -> Category:
    """Create a new category inside a group.

    Args:
        db: Async database session.
        schema: Validated category creation schema (includes group_id).

    Returns:
        Newly created Category instance.
    """
    category = Category(
        group_id=schema.group_id,
        name=schema.name,
        sort_order=schema.sort_order,
        hidden=schema.hidden,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(
    db: AsyncSession, category: Category, schema: CategoryUpdate
) -> Category:
    """Partially update a category.

    Args:
        db: Async database session.
        category: Existing Category instance.
        schema: Partial update schema.

    Returns:
        Updated Category instance.
    """
    for field, value in schema.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category: Category) -> None:
    """Delete a category.

    Args:
        db: Async database session.
        category: Category instance to delete.
    """
    await db.delete(category)
    await db.commit()
