"""Pydantic schemas for CategoryRule model."""

import re
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

# Heuristic pattern that detects catastrophically backtracking constructs such as
# ``(X+)+``, ``(X*)*``, ``(X+)*``.  These are rejected to mitigate ReDoS attacks.
_REDOS_HEURISTIC = re.compile(r"\([^()]*[+*][^()]*\)[+*?]")

MatchField = Literal["payee", "memo"]
MatchType = Literal["contains", "exact", "regex"]
TransactionType = Literal["any", "debit", "credit"]


class CategoryRuleCreate(BaseModel):
    """Schema for creating a categorization rule.

    Attributes:
        pattern: Text pattern to match against.
        match_field: Field to match (payee or memo).
        match_type: Type of matching (contains, exact, regex).
        category_id: Category to assign on match.
        priority: Higher priority rules are evaluated first.
        transaction_type: Sign filter — ``"any"`` matches both debits and
            credits; ``"debit"`` restricts to negative amounts; ``"credit"``
            restricts to positive amounts.
        min_amount: Optional lower bound on abs(amount) in centimes (inclusive).
        max_amount: Optional upper bound on abs(amount) in centimes (inclusive).
    """

    pattern: str = Field(..., min_length=1, max_length=100)
    match_field: MatchField
    match_type: MatchType
    category_id: int
    priority: int = 0
    transaction_type: TransactionType = "any"
    min_amount: int | None = Field(default=None, ge=0)
    max_amount: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_amount_range(self) -> Self:
        """Ensure min_amount <= max_amount when both are provided."""
        if (
            self.min_amount is not None
            and self.max_amount is not None
            and self.min_amount > self.max_amount
        ):
            raise ValueError("min_amount must be <= max_amount")
        return self

    @model_validator(mode="after")
    def validate_regex_pattern(self) -> Self:
        """Validate regex patterns for syntax errors and ReDoS risk.

        Only applies when ``match_type`` is ``"regex"``.
        """
        if self.match_type != "regex":
            return self
        try:
            re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"Invalid regex pattern: {exc}") from exc
        if _REDOS_HEURISTIC.search(self.pattern):
            raise ValueError(
                "Regex pattern may cause catastrophic backtracking (ReDoS). "
                "Avoid nested quantifiers such as (X+)+ or (X*)*."
            )
        return self


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
        transaction_type: Sign filter for this rule.
        min_amount: Optional lower bound on abs(amount) in centimes.
        max_amount: Optional upper bound on abs(amount) in centimes.
    """

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    pattern: str
    match_field: str
    match_type: str
    category_id: int
    priority: int
    transaction_type: str = "any"
    min_amount: int | None = None
    max_amount: int | None = None


class CategoryRuleUpdate(BaseModel):
    """Schema for partially updating a categorization rule.

    Attributes:
        pattern: New pattern text.
        match_field: New match field.
        match_type: New match type.
        category_id: New target category.
        priority: New priority.
        transaction_type: New sign filter.
        min_amount: New lower bound on abs(amount) in centimes.
        max_amount: New upper bound on abs(amount) in centimes.
    """

    pattern: str | None = Field(None, min_length=1, max_length=200)
    match_field: MatchField | None = None
    match_type: MatchType | None = None
    category_id: int | None = None
    priority: int | None = None
    transaction_type: TransactionType | None = None
    min_amount: int | None = Field(default=None, ge=0)
    max_amount: int | None = Field(default=None, ge=0)
