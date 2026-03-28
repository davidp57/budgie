"""Pydantic schemas for Transaction and SplitTransaction models."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

ClearedStatus = Literal["uncleared", "cleared", "reconciled"]
TransactionStatus = Literal["planned", "real", "reconciled"]


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction.

    Amounts are in integer centimes (e.g., -5050 = -50.50€).

    Attributes:
        account_id: Account the transaction belongs to.
        date: Transaction date.
        payee_id: Optional payee reference.
        category_id: Optional category for budgeting.
        amount: Amount in integer centimes.
        memo: Optional memo/description.
        cleared: Cleared status (uncleared/cleared/reconciled).
        is_virtual: Whether this is a planned future transaction.
        virtual_linked_id: Links to a real transaction (for virtual).
        import_hash: Unique hash for deduplication.
    """

    account_id: int
    date: datetime.date
    payee_id: int | None = None
    category_id: int | None = None
    envelope_id: int | None = None
    amount: int
    memo: str | None = Field(None, max_length=500)
    cleared: ClearedStatus = "uncleared"
    is_virtual: bool = False
    virtual_linked_id: int | None = None
    status: TransactionStatus = "real"
    import_hash: str | None = None


class TransactionUpdate(BaseModel):
    """Schema for partially updating a transaction.

    Attributes:
        date: New transaction date.
        payee_id: New payee reference.
        category_id: New category.
        amount: New amount in centimes.
        memo: New memo.
        cleared: New cleared status.
        is_virtual: New virtual flag.
    """

    date: datetime.date | None = None
    payee_id: int | None = None
    category_id: int | None = None
    envelope_id: int | None = None
    amount: int | None = None
    memo: str | None = Field(None, max_length=500)
    cleared: ClearedStatus | None = None
    is_virtual: bool | None = None
    status: TransactionStatus | None = None
    income_for_month: str | None = None


class TransactionLinkedInfo(BaseModel):
    """Compact info about a linked bank transaction.

    Attributes:
        id: Transaction ID of the linked bank import.
        memo: Memo/description from the bank.
        amount: Amount in integer centimes.
        date: Date of the bank transaction.
    """

    model_config = {"from_attributes": True}

    id: int
    memo: str | None
    amount: int
    date: datetime.date


class TransactionRead(BaseModel):
    """Schema for reading transaction data (response).

    Attributes:
        id: Transaction ID.
        account_id: Account ID.
        date: Transaction date.
        payee_id: Payee ID.
        category_id: Category ID.
        amount: Amount in integer centimes.
        memo: Memo text.
        status: Transaction status (planned/real/reconciled).
        cleared: Deprecated — kept for backward compatibility.
        is_virtual: Deprecated — kept for backward compatibility.
        virtual_linked_id: Deprecated — kept for backward compatibility.
        income_for_month: Budget month this income is assigned to (YYYY-MM), if any.
        import_hash: Import deduplication hash.
        reconciled_with_id: ID of the linked bank transaction (when pointed).
        linked_transaction: Compact bank transaction info when pointed.
        created_at: Creation timestamp.
    """

    model_config = {"from_attributes": True}

    id: int
    account_id: int
    date: datetime.date
    payee_id: int | None
    category_id: int | None
    envelope_id: int | None
    amount: int
    memo: str | None
    status: str = "real"
    cleared: str = "uncleared"
    is_virtual: bool = False
    virtual_linked_id: int | None = None
    income_for_month: str | None = None
    import_hash: str | None = None
    reconciled_with_id: int | None = None
    linked_transaction: TransactionLinkedInfo | None = None
    created_at: datetime.datetime


class SplitTransactionCreate(BaseModel):
    """Schema for creating a split transaction line.

    Attributes:
        category_id: Category for this split.
        amount: Amount in integer centimes.
        memo: Optional memo.
    """

    category_id: int | None = None
    amount: int
    memo: str | None = Field(None, max_length=500)


class SplitTransactionRead(BaseModel):
    """Schema for reading a split transaction line (response).

    Attributes:
        id: Split ID.
        parent_id: Parent transaction ID.
        category_id: Category ID.
        amount: Amount in centimes.
        memo: Memo text.
    """

    model_config = {"from_attributes": True}

    id: int
    parent_id: int
    category_id: int | None
    amount: int
    memo: str | None


class PlannedMatchRequest(BaseModel):
    """Schema for linking a real transaction to a planned one.

    Attributes:
        real_transaction_id: ID of the real (imported) transaction.
        planned_transaction_id: ID of the planned transaction to link.
    """

    real_transaction_id: int
    planned_transaction_id: int
