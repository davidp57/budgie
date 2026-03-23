"""Pydantic schemas for the Envelope model."""

from typing import Literal

from pydantic import BaseModel, Field

EnvelopeType = Literal["regular", "cumulative", "reserve"]
EnvelopePeriod = Literal["weekly", "monthly", "quarterly", "yearly"]


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
        envelope_type: Type — regular, cumulative, or reserve.
        period: Budget allocation period.
        target_amount: Optional goal amount in centimes.
        stop_on_target: Stop allocating when target is reached.
        rollover: When True, unspent balance carries over to next month.
        sort_order: UI display order (default 0).
        category_ids: Categories to associate with this envelope.
    """

    name: str = Field(..., min_length=1, max_length=100)
    envelope_type: EnvelopeType = "regular"
    period: EnvelopePeriod = "monthly"
    target_amount: int | None = None
    stop_on_target: bool = False
    rollover: bool = False
    sort_order: int = 0
    emoji: str = Field(default="📦", max_length=10)
    category_ids: list[int] = Field(default_factory=list)


class EnvelopeUpdate(BaseModel):
    """Schema for updating an envelope (all fields optional).

    Attributes:
        name: New display name.
        envelope_type: New envelope type.
        period: New allocation period.
        target_amount: New target amount in centimes.
        stop_on_target: New stop-on-target flag.
        rollover: New rollover setting.
        sort_order: New display order.
        category_ids: Replacement category list (replaces all existing links).
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    envelope_type: EnvelopeType | None = None
    period: EnvelopePeriod | None = None
    target_amount: int | None = None
    stop_on_target: bool | None = None
    rollover: bool | None = None
    sort_order: int | None = None
    emoji: str | None = Field(default=None, max_length=10)
    category_ids: list[int] | None = None


class EnvelopeRead(BaseModel):
    """Schema for reading an envelope (response).

    Attributes:
        id: Envelope primary key.
        name: Display name.
        envelope_type: Envelope type (regular/cumulative/reserve).
        period: Budget allocation period.
        target_amount: Goal amount in centimes, if any.
        stop_on_target: Whether allocating stops at target.
        rollover: Whether unspent balance carries over.
        sort_order: UI display order.
        categories: Categories linked to this envelope.
    """

    model_config = {"from_attributes": True}

    id: int
    name: str
    envelope_type: str
    period: str
    target_amount: int | None
    stop_on_target: bool
    rollover: bool
    sort_order: int
    emoji: str = "📦"
    categories: list[CategoryRef]
