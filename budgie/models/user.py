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
        created_at: Timestamp of account creation.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
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
