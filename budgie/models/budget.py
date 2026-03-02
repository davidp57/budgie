"""BudgetAllocation ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.category import Category


class BudgetAllocation(Base):
    """Monthly budget allocation for a category (envelope budgeting).

    Amounts are stored as integer centimes (e.g., 15000 = 150.00€).

    Attributes:
        id: Primary key.
        category_id: The category receiving the budget allocation.
        month: Budget month in YYYY-MM format.
        budgeted: Amount budgeted in integer centimes.
    """

    __tablename__ = "budget_allocations"
    __table_args__ = (
        UniqueConstraint("category_id", "month", name="uq_category_month"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    budgeted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    category: Mapped[Category] = relationship()
