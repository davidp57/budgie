"""Pydantic schemas for Category and CategoryGroup models."""

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    """Schema for creating a new category.

    Attributes:
        name: Display name of the category.
        group_id: Parent category group ID.
        sort_order: Order for UI display.
        hidden: Whether the category is hidden.
    """

    name: str = Field(..., min_length=1, max_length=100)
    group_id: int
    sort_order: int = 0
    hidden: bool = False


class CategoryRead(BaseModel):
    """Schema for reading a category (response).

    Attributes:
        id: Category ID.
        group_id: Parent category group ID.
        name: Display name.
        sort_order: UI display order.
        hidden: Whether the category is hidden.
    """

    model_config = {"from_attributes": True}

    id: int
    group_id: int
    name: str
    sort_order: int
    hidden: bool


class CategoryUpdate(BaseModel):
    """Schema for partially updating a category.

    Attributes:
        name: New display name.
        sort_order: New sort order.
        hidden: New hidden flag.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = None
    hidden: bool | None = None


class CategoryGroupCreate(BaseModel):
    """Schema for creating a new category group.

    Attributes:
        name: Display name of the group.
        sort_order: Order for UI display.
    """

    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = 0


class CategoryGroupRead(BaseModel):
    """Schema for reading a category group with its categories (response).

    Attributes:
        id: Group ID.
        user_id: Owner user ID.
        name: Display name.
        sort_order: UI display order.
        categories: List of categories in this group.
    """

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    sort_order: int
    categories: list[CategoryRead] = []
