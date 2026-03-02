"""Pydantic schemas for the Envelope model."""

from pydantic import BaseModel, Field


class CategoryRef(BaseModel):
    """Minimal category reference used inside envelope responses.

    Attributes:
        id: Category primary key.
        name: Category display name.
        group_name: Parent group display name.
    """

    model_config = {"from_attributes": True}

    id: int
    name: str
    group_name: str


class EnvelopeCreate(BaseModel):
    """Schema for creating a new envelope.

    Attributes:
        name: Display name of the envelope.
        rollover: When True, unspent balance carries over to next month.
        sort_order: UI display order (default 0).
        category_ids: Categories to associate with this envelope.
    """

    name: str = Field(..., min_length=1, max_length=100)
    rollover: bool = False
    sort_order: int = 0
    category_ids: list[int] = Field(default_factory=list)


class EnvelopeUpdate(BaseModel):
    """Schema for updating an envelope (all fields optional).

    Attributes:
        name: New display name.
        rollover: New rollover setting.
        sort_order: New display order.
        category_ids: Replacement category list (replaces all existing links).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    rollover: bool | None = None
    sort_order: int | None = None
    category_ids: list[int] | None = None


class EnvelopeRead(BaseModel):
    """Schema for reading an envelope (response).

    Attributes:
        id: Envelope primary key.
        name: Display name.
        rollover: Whether unspent balance carries over.
        sort_order: UI display order.
        categories: Categories linked to this envelope.
    """

    model_config = {"from_attributes": True}

    id: int
    name: str
    rollover: bool
    sort_order: int
    categories: list[CategoryRef]
