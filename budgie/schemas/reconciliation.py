"""Pydantic schemas for the reconciliation (pointage) feature."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

from budgie.schemas.category_rule import CategoryRuleRead

ReconciliationStatus = Literal["unlinked", "suggested", "linked"]


class BankTxRead(BaseModel):
    """A bank-imported transaction as presented in the reconciliation view."""

    model_config = {"from_attributes": True}

    id: int
    date: datetime.date
    label: str
    amount: int  # centimes
    import_hash: str | None


class BudgetExpenseRead(BaseModel):
    """A budget transaction as presented in the reconciliation view."""

    model_config = {"from_attributes": True}

    id: int
    date: datetime.date
    label: str
    amount: int  # centimes
    category_id: int | None
    category_name: str | None
    memo: str | None
    status: str  # planned, real, reconciled


class SuggestionRead(BaseModel):
    """A rule-based pairing suggestion between a bank tx and a budget expense."""

    bank_tx: BankTxRead
    expense: BudgetExpenseRead
    score: float = Field(..., description="Matching score (higher is better)")


class ReconciliationViewResponse(BaseModel):
    """Full reconciliation view payload for a given account and month."""

    account_id: int
    month: str
    bank_txs: list[BankTxRead]
    expenses: list[BudgetExpenseRead]
    links: list["LinkRead"]
    suggestions: list[SuggestionRead]


class LinkRead(BaseModel):
    """A confirmed link between a bank transaction and a budget expense."""

    bank_tx_id: int
    expense_id: int
    created_rule: CategoryRuleRead | None = None


class LinkRequest(BaseModel):
    """Request body to create a reconciliation link."""

    bank_tx_id: int
    expense_id: int
    adjust_amount: bool = Field(
        default=True,
        description="If True, update the expense amount to match the bank transaction.",
    )
    memo: str | None = Field(default=None, max_length=500)


class ClotureRequest(BaseModel):
    """Request body to finalise (clôturer) a reconciliation session."""

    account_id: int
    month: str


class ClotureResponse(BaseModel):
    """Summary returned after finalising a reconciliation session."""

    linked_count: int
    total_bank_txs: int
    total_expenses: int
    reconciled_count: int
