"""Pydantic schemas for Payee model."""

from pydantic import BaseModel, Field


class PayeeCreate(BaseModel):
    """Schema for creating a new payee.

    Attributes:
        name: Display name of the payee.
        auto_category_id: Default category ID (optional).
    """

    name: str = Field(..., min_length=1, max_length=200)
    auto_category_id: int | None = None


class PayeeRead(BaseModel):
    """Schema for reading payee data (response).

    Attributes:
        id: Payee ID.
        user_id: Owner user ID.
        name: Display name.
        auto_category_id: Default category ID.
    """

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    auto_category_id: int | None = None


class PayeeUpdate(BaseModel):
    """Schema for partially updating a payee.

    Attributes:
        name: New display name.
        auto_category_id: New default category ID.
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    auto_category_id: int | None = None
