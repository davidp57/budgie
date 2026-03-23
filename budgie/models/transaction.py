"""Transaction and SplitTransaction ORM models."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.account import Account
    from budgie.models.category import Category
    from budgie.models.payee import Payee


class Transaction(Base):
    """Represents a financial transaction in an account.

    Amounts are stored as integer centimes (e.g., -5050 = -50.50€).

    Attributes:
        id: Primary key.
        account_id: The account this transaction belongs to.
        date: Date of the transaction.
        payee_id: Optional payee reference.
        category_id: Optional category for budgeting.
        amount: Amount in integer centimes (negative = expense).
        memo: Optional memo/description.
        status: Transaction status — planned (future), real, or reconciled.
        income_for_month: When set (YYYY-MM), this real transaction income is
            counted toward that month ``to_be_budgeted`` (N+1 mode).
        import_hash: Unique hash for deduplication during import.
        created_at: Timestamp of record creation.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    payee_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("payees.id"), nullable=True, default=None
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, default=None
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="real")
    income_for_month: Mapped[str | None] = mapped_column(
        String(7), nullable=True, default=None
    )
    import_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    account: Mapped[Account] = relationship(back_populates="transactions")
    payee: Mapped[Payee | None] = relationship()
    category: Mapped[Category | None] = relationship()
    splits: Mapped[list[SplitTransaction]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )


class SplitTransaction(Base):
    """A sub-line of a split transaction, each with its own category.

    Amounts are stored as integer centimes.

    Attributes:
        id: Primary key.
        parent_id: The parent transaction being split.
        category_id: Category for this split portion.
        amount: Amount in integer centimes.
        memo: Optional memo for this split.
    """

    __tablename__ = "split_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"), nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, default=None
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)

    # Relationships
    parent: Mapped[Transaction] = relationship(back_populates="splits")
    category: Mapped[Category | None] = relationship()
