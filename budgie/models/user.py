"""User ORM model."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.account import Account
    from budgie.models.category import CategoryGroup
    from budgie.models.category_rule import CategoryRule
    from budgie.models.payee import Payee


class User(Base):
    """Represents an application user.

    Attributes:
        id: Primary key.
        username: Unique username for login.
        hashed_password: Bcrypt-hashed password.
        budget_mode: Budgeting mode — ``n1`` (N+1, default: income from M-1 feeds
            current month) or ``n`` (prévisionnel: virtual transactions created
            for income expected in the current month).
        created_at: Timestamp of account creation.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    budget_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, default="n1", server_default="n1"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    accounts: Mapped[list[Account]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    category_groups: Mapped[list[CategoryGroup]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payees: Mapped[list[Payee]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    category_rules: Mapped[list[CategoryRule]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
