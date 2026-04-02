"""Payee ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.category import Category
    from budgie.models.user import User


class Payee(Base):
    """Represents a transaction payee (merchant, person, etc.).

    Attributes:
        id: Primary key.
        user_id: Owner of the payee record.
        name: Display name of the payee.
        auto_category_id: Default category to assign for this payee (nullable).
    """

    __tablename__ = "payees"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    auto_category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id"), nullable=True, default=None
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="payees")
    auto_category: Mapped[Category | None] = relationship()
