"""CategoryRule ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.category import Category
    from budgie.models.user import User


class CategoryRule(Base):
    """Rule for automatic transaction categorization.

    Rules are evaluated in descending priority order.

    Attributes:
        id: Primary key.
        user_id: Owner of the rule.
        pattern: Text pattern to match against.
        match_field: Field to match (payee or memo).
        match_type: Type of matching (contains, exact, regex).
        category_id: Category to assign when the rule matches.
        priority: Higher priority rules are evaluated first.
    """

    __tablename__ = "category_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    pattern: Mapped[str] = mapped_column(String(200), nullable=False)
    match_field: Mapped[str] = mapped_column(String(20), nullable=False)  # payee, memo
    match_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # contains, exact, regex
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped[User] = relationship(back_populates="category_rules")
    category: Mapped[Category] = relationship()
