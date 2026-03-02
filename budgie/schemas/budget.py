"""Pydantic schemas for BudgetAllocation model."""

from pydantic import BaseModel, Field, field_validator

from budgie.schemas.envelope import CategoryRef


class BudgetAllocationRead(BaseModel):
    """Schema for reading a budget allocation (response).

    Attributes:
        id: Allocation ID.
        envelope_id: Envelope ID.
        month: Budget month in YYYY-MM format.
        budgeted: Amount budgeted in centimes.
    """

    model_config = {"from_attributes": True}

    id: int
    envelope_id: int
    month: str
    budgeted: int


class BudgetAllocationUpdate(BaseModel):
    """Schema for updating a budget allocation amount.

    Attributes:
        budgeted: New budgeted amount in integer centimes (must be >= 0).
    """

    budgeted: int = Field(..., ge=0)


class BudgetLineInput(BaseModel):
    """A single line in a budget PUT request (envelope + amount).

    Attributes:
        envelope_id: Envelope to allocate budget for.
        budgeted: Amount in integer centimes (must be >= 0).
    """

    envelope_id: int
    budgeted: int = Field(..., ge=0)

    @field_validator("budgeted")
    @classmethod
    def validate_budgeted(cls, v: int) -> int:
        """Ensure budgeted amount is non-negative.

        Args:
            v: The budgeted value.

        Returns:
            The validated value.
        """
        return v


class EnvelopeLineRead(BaseModel):
    """Per-envelope budget line with budgeted, activity, and available amounts.

    Used in the full month budget view returned by GET /api/budget/{month}.
    Amounts are in integer centimes.

    Attributes:
        envelope_id: Envelope primary key.
        envelope_name: Display name of the envelope.
        rollover: Whether unspent balance carries over to the next month.
        categories: Categories linked to this envelope.
        budgeted: Amount budgeted for this specific month (centimes).
        activity: Sum of transactions (including virtual) for this month (centimes).
        available: Available amount (centimes). With rollover=True, cumulative
            across all months ≤ current. With rollover=False, current month only.
    """

    envelope_id: int
    envelope_name: str
    rollover: bool
    categories: list[CategoryRef]
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
        envelopes: Envelope list ordered by sort_order.
    """

    month: str
    to_be_budgeted: int
    envelopes: list[EnvelopeLineRead]
