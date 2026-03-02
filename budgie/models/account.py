"""Account ORM model."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.transaction import Transaction
    from budgie.models.user import User


class Account(Base):
    """Represents a financial account (checking, savings, credit, cash).

    Attributes:
        id: Primary key.
        user_id: Owner of the account.
        name: Display name of the account.
        account_type: Type of account (checking, savings, credit, cash).
        on_budget: Whether transactions in this account affect the budget.
        created_at: Timestamp of account creation.
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    on_budget: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="accounts")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
