"""Category and CategoryGroup ORM models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.user import User


class CategoryGroup(Base):
    """A group of budget categories (e.g., Bills, Food, Transport).

    Attributes:
        id: Primary key.
        user_id: Owner of the category group.
        name: Display name.
        sort_order: Order for UI display.
    """

    __tablename__ = "category_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user: Mapped[User] = relationship(back_populates="category_groups")
    categories: Mapped[list[Category]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Category(Base):
    """A budget category within a group (e.g., Electricity, Groceries).

    Attributes:
        id: Primary key.
        group_id: Parent category group.
        name: Display name.
        sort_order: Order for UI display.
        hidden: Whether the category is hidden from the budget view.
    """

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("category_groups.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    group: Mapped[CategoryGroup] = relationship(back_populates="categories")
