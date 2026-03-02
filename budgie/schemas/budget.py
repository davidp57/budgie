"""Pydantic schemas for BudgetAllocation model."""

from pydantic import BaseModel, Field, field_validator


class BudgetAllocationCreate(BaseModel):
    """Schema for creating or updating a budget allocation.

    Amounts are in integer centimes (e.g., 15000 = 150.00€).

    Attributes:
        category_id: Category receiving the allocation.
        month: Budget month in YYYY-MM format.
        budgeted: Amount budgeted in integer centimes (must be >= 0).
    """

    category_id: int
    month: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    budgeted: int = Field(..., ge=0)

    @field_validator("month")
    @classmethod
    def validate_month_format(cls, v: str) -> str:
        """Ensure month is in YYYY-MM format.

        Args:
            v: The month string to validate.

        Returns:
            The validated month string.
        """
        return v


class BudgetAllocationRead(BaseModel):
    """Schema for reading a budget allocation (response).

    Attributes:
        id: Allocation ID.
        category_id: Category ID.
        month: Budget month in YYYY-MM format.
        budgeted: Amount budgeted in centimes.
    """

    model_config = {"from_attributes": True}

    id: int
    category_id: int
    month: str
    budgeted: int


class BudgetAllocationUpdate(BaseModel):
    """Schema for updating a budget allocation amount.

    Attributes:
        budgeted: New budgeted amount in integer centimes (must be >= 0).
    """

    budgeted: int = Field(..., ge=0)


class BudgetLineInput(BaseModel):
    """A single line in a budget PUT request (category + amount).

    Attributes:
        category_id: Category to allocate budget for.
        budgeted: Amount in integer centimes (must be >= 0).
    """

    category_id: int
    budgeted: int = Field(..., ge=0)


class EnvelopeLineRead(BaseModel):
    """Per-category envelope with budgeted, activity, and available amounts.

    Used in the full month budget view returned by GET /api/budget/{month}.
    Amounts are in integer centimes.

    Attributes:
        category_id: Category primary key.
        category_name: Display name of the category (denormalized for UI).
        group_id: Parent category group primary key.
        group_name: Display name of the category group (denormalized for UI).
        budgeted: Amount budgeted for this specific month (centimes).
        activity: Sum of transactions (including virtual) for this month (centimes).
        available: Cumulative Σ(budgeted - activity) through this month (centimes).
    """

    category_id: int
    category_name: str
    group_id: int
    group_name: str
    budgeted: int
    activity: int
    available: int


class MonthBudgetResponse(BaseModel):
    """Full budget view for a given month, including all envelopes.

    Returned by GET /api/budget/{month}.
    Amounts are in integer centimes.

    Attributes:
        month: Budget month in YYYY-MM format.
        to_be_budgeted: Income received this month minus total amount budgeted.
            Goal is 0 (every centime assigned to an envelope).
        envelopes: Per-category envelope list ordered by group/category sort_order.
    """

    month: str
    to_be_budgeted: int
    envelopes: list[EnvelopeLineRead]
