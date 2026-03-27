"""Pydantic schemas for the reconciliation (pointage) feature."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

from budgie.schemas.category_rule import CategoryRuleRead, TransactionType

#: How the auto-created rule's amount constraint should be derived.
RuleAmountMode = Literal["none", "exact", "percent"]

ReconciliationStatus = Literal["unlinked", "suggested", "linked"]


class BankTxRead(BaseModel):
    """A bank-imported transaction as presented in the reconciliation view."""

    model_config = {"from_attributes": True}

    id: int
    date: datetime.date
    label: str
    amount: int  # centimes
    import_hash: str | None
    rule_pattern: str | None = None  # cleaned pattern for rule-creation preview


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


class RuleMatchRead(BaseModel):
    """A bank tx matched by a rule but with no existing expense to pair with."""

    bank_tx: BankTxRead
    category_id: int
    category_name: str | None = None


class ReconciliationViewResponse(BaseModel):
    """Full reconciliation view payload for a given account and month."""

    account_id: int
    month: str
    bank_txs: list[BankTxRead]
    expenses: list[BudgetExpenseRead]
    links: list["LinkRead"]
    suggestions: list[SuggestionRead]
    rule_matches: list[RuleMatchRead] = []


class LinkRead(BaseModel):
    """A confirmed link between a bank transaction and a budget expense."""

    bank_tx_id: int
    expense_id: int
    created_rule: CategoryRuleRead | None = None


class LinkRequest(BaseModel):
    """Request body to create a reconciliation link.

    Attributes:
        bank_tx_id: Bank-imported transaction to link.
        expense_id: Budget expense to link.
        adjust_amount: Whether to adjust the expense amount to match the bank tx.
        memo: Optional memo to set on the expense.
        rule_transaction_type: Sign filter for the auto-created rule.
        rule_amount_mode: How to derive the rule's amount constraint.
        rule_amount_tolerance_pct: Tolerance percentage when mode is ``percent``.
        skip_rule: If True, do not auto-create a categorization rule.
    """

    bank_tx_id: int
    expense_id: int
    adjust_amount: bool = Field(
        default=True,
        description="If True, update the expense amount to match the bank transaction.",
    )
    memo: str | None = Field(default=None, max_length=500)
    rule_transaction_type: TransactionType = "any"
    rule_amount_mode: RuleAmountMode = "none"
    rule_amount_tolerance_pct: int = Field(default=10, ge=1, le=99)
    skip_rule: bool = False


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
