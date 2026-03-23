"""Pydantic schemas for Account model."""

import datetime
from typing import Literal

from pydantic import BaseModel, Field

AccountType = Literal["checking", "savings", "credit", "cash", "wallet"]


class AccountCreate(BaseModel):
    """Schema for creating a new account.

    Attributes:
        name: Display name of the account.
        account_type: Type (checking, savings, credit, cash).
        on_budget: Whether the account is on-budget.
    """

    name: str = Field(..., min_length=1, max_length=100)
    account_type: AccountType
    on_budget: bool = True


class AccountUpdate(BaseModel):
    """Schema for partially updating an account.

    All fields are optional.

    Attributes:
        name: New display name.
        account_type: New account type.
        on_budget: New on-budget flag.
    """

    name: str | None = Field(None, min_length=1, max_length=100)
    account_type: AccountType | None = None
    on_budget: bool | None = None


class AccountRead(BaseModel):
    """Schema for reading account data (response).

    Attributes:
        id: Account ID.
        user_id: Owner user ID.
        name: Display name.
        account_type: Account type.
        on_budget: Whether the account is on-budget.
        created_at: Creation timestamp.
    """

    model_config = {"from_attributes": True}

    id: int
    user_id: int
    name: str
    account_type: str
    on_budget: bool
    created_at: datetime.datetime
