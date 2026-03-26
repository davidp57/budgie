"""Envelope ORM model for budget envelope system.

An Envelope is a named budget unit that can contain one or more Categories.
Transactions are tagged with Categories; budget allocations are on Envelopes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

#: Valid envelope types.
ENVELOPE_TYPES = ("regular", "cumulative", "reserve")
#: Valid allocation periods.
ENVELOPE_PERIODS = ("weekly", "monthly", "quarterly", "yearly")

if TYPE_CHECKING:
    from budgie.models.budget import BudgetAllocation
    from budgie.models.category import Category


# Association table: which categories belong to which envelope.
# A category belongs to at most one envelope (enforced at the service layer).
envelope_categories = Table(
    "envelope_categories",
    Base.metadata,
    Column(
        "envelope_id",
        Integer,
        ForeignKey("envelopes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        Integer,
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Envelope(Base):
    """Budget envelope: a named unit receiving monthly budget allocations.

    Can contain one or more Categories; transactions are tagged with
    categories, while budget amounts are tracked per envelope per month.

    Attributes:
        id: Primary key.
        user_id: Owner user ID (FK → users.id).
        name: Display name of the envelope.
        envelope_type: Type of envelope — regular (monthly reset), cumulative
            (balance carries over) or reserve (no periodic allocation).
        period: Budget allocation period (weekly/monthly/quarterly/yearly).
        target_amount: Optional goal amount in centimes (cumulative only).
        stop_on_target: Stop allocating when target is reached.
        rollover: When True, unspent balance carries over to the next month.
            When False (default), available resets to budgeted each month.
        sort_order: UI display order.
        categories: Categories linked to this envelope (M2M).
        allocations: Monthly budget allocations for this envelope.
    """

    __tablename__ = "envelopes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    envelope_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="regular"
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    target_amount: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )
    stop_on_target: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollover: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emoji: Mapped[str] = mapped_column(String(10), nullable=False, default="📦")
    color_index: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None
    )

    categories: Mapped[list[Category]] = relationship(
        "Category",
        secondary=envelope_categories,
        lazy="selectin",
    )
    allocations: Mapped[list[BudgetAllocation]] = relationship(
        "BudgetAllocation",
        back_populates="envelope",
        cascade="all, delete-orphan",
    )
