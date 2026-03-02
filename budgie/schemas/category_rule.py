"""Pydantic schemas for CategoryRule model."""

from typing import Literal

from pydantic import BaseModel, Field

MatchField = Literal["payee", "memo"]
MatchType = Literal["contains", "exact", "regex"]


class CategoryRuleCreate(BaseModel):
    """Schema for creating a categorization rule.

    Attributes:
        pattern: Text pattern to match against.
        match_field: Field to match (payee or memo).
        match_type: Type of matching (contains, exact, regex).
        category_id: Category to assign on match.
        priority: Higher priority rules are evaluated first.
    """

    pattern: str = Field(..., min_length=1, max_length=200)
    match_field: MatchField
    match_type: MatchType
    category_id: int
    priority: int = 0


class CategoryRuleRead(BaseModel):
    """Schema for reading a categorization rule (response).

    Attributes:
        id: Rule ID.
        user_id: Owner user ID.
        pattern: Pattern text.
        match_field: Field to match.
        match_type: Match type.
        category_id: Target category ID.
        priority: Rule priority.
    """

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    pattern: str
    match_field: str
    match_type: str
    category_id: int
    priority: int


class CategoryRuleUpdate(BaseModel):
    """Schema for partially updating a categorization rule.

    Attributes:
        pattern: New pattern text.
        match_field: New match field.
        match_type: New match type.
        category_id: New target category.
        priority: New priority.
    """

    pattern: str | None = Field(None, min_length=1, max_length=200)
    match_field: MatchField | None = None
    match_type: MatchType | None = None
    category_id: int | None = None
    priority: int | None = None
