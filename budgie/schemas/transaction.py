"""Pydantic schemas for Transaction and SplitTransaction models."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

ClearedStatus = Literal["uncleared", "cleared", "reconciled"]


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
    amount: int
    memo: str | None = Field(None, max_length=500)
    cleared: ClearedStatus = "uncleared"
    is_virtual: bool = False
    virtual_linked_id: int | None = None
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
    amount: int | None = None
    memo: str | None = Field(None, max_length=500)
    cleared: ClearedStatus | None = None
    is_virtual: bool | None = None


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
        cleared: Cleared status.
        is_virtual: Whether virtual.
        virtual_linked_id: Linked transaction ID.
        import_hash: Import deduplication hash.
        created_at: Creation timestamp.
    """

    model_config = {"from_attributes": True}

    id: int
    account_id: int
    date: datetime.date
    payee_id: int | None
    category_id: int | None
    amount: int
    memo: str | None
    cleared: str
    is_virtual: bool
    virtual_linked_id: int | None
    import_hash: str | None
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
