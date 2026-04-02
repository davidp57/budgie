"""Pydantic schemas for BudgetAllocation model."""

from pydantic import BaseModel, Field, field_validator

from budgie.schemas.envelope import CategoryRef

#: Accepted format for budget month parameters: ``YYYY-MM``.
MONTH_PATTERN: str = r"^\d{4}-(0[1-9]|1[0-2])$"


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
        envelope_type: Type of envelope (regular/cumulative/reserve).
        rollover: Whether unspent balance carries over to the next month.
        categories: Categories linked to this envelope.
        budgeted: Amount budgeted for this specific month (centimes).
        activity: Sum of transactions for this month (centimes).
        available: Available amount (centimes). With rollover=True, cumulative
            across all months ≤ current. With rollover=False, current month only.
        expense_count: Number of manually-created expense transactions assigned
            to this envelope for the month.
    """

    envelope_id: int
    envelope_name: str
    envelope_type: str = "regular"
    emoji: str = "📦"
    color_index: int | None = None
    rollover: bool
    target_amount: int | None = None
    categories: list[CategoryRef]
    budgeted: int
    activity: int
    available: int
    expense_count: int = 0
    is_budget_inherited: bool = False


class MonthBudgetResponse(BaseModel):
    """Full budget view for a given month, including all envelopes.

    Returned by GET /api/budget/{month}.
    Amounts are in integer centimes.

    Attributes:
        month: Budget month in YYYY-MM format.
        to_be_budgeted: Income received this month minus total amount budgeted.
            Goal is 0 (every centime assigned to an envelope).
        total_available: Sum of all envelope available amounts this month.
            Positive means money is available across envelopes; negative means
            envelopes are collectively over-spent.
        envelopes: Envelope list ordered by sort_order.
    """

    month: str
    to_be_budgeted: int
    total_available: int
    envelopes: list[EnvelopeLineRead]


class AssignIncomeRequest(BaseModel):
    """Request body for POST /api/budget/{month}/assign-income.

    Used in N+1 budgeting mode: marks existing transactions from M-1 as
    counting toward the target month's ``to_be_budgeted``.

    Attributes:
        transaction_ids: IDs of the real transactions to tag with
            ``income_for_month``.
    """

    transaction_ids: list[int]


class IncomeProposal(BaseModel):
    """A single income proposal drawn from M-1 transactions.

    Represents a positive transaction from the previous month that may be
    repeated as a planned (virtual) income transaction for the current month.
    Amounts are in integer centimes.

    Attributes:
        transaction_id: Source transaction ID from M-1.
        date: Original transaction date (YYYY-MM-DD).
        amount: Amount in centimes (always positive).
        memo: Optional transaction memo.
        account_id: Source account ID.
    """

    transaction_id: int
    date: str
    amount: int
    memo: str | None
    account_id: int


class IncomeProposalsResponse(BaseModel):
    """Response for GET /api/budget/{month}/income-proposals.

    Attributes:
        month: The current budget month (YYYY-MM).
        previous_month: Previous month from which proposals are drawn (YYYY-MM).
        threshold_centimes: Minimum amount used to filter proposals.
        proposals: List of income proposals ordered by amount descending.
    """

    month: str
    previous_month: str
    threshold_centimes: int
    proposals: list[IncomeProposal]
