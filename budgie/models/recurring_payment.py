"""RecurringPayment ORM model."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from budgie.database import Base

if TYPE_CHECKING:
    from budgie.models.category import Category
    from budgie.models.user import User


class RecurringPayment(Base):
    """A recurring bank debit the user has classified.

    The debits themselves are not linked: they are found again at each read
    by their normalized label (``match_key``) and amount, so that newly
    imported transactions are followed without any extra step.

    Attributes:
        id: Primary key.
        user_id: Owner of the payment.
        name: Display name chosen by the user (encrypted at rest).
        match_key: Normalized bank label of the debits (encrypted at rest).
        amount: Reference amount per period, in positive integer centimes.
        period: Billing rhythm: ``monthly``, ``quarterly`` or ``yearly``.
        kind: ``subscription``, ``other`` (recurring but not a subscription:
            taxes, savings, insurance) or ``dismissed`` (not to be proposed again).
        category_id: Optional category, for display.
        cancelled_at: Cancellation date declared by the user, if any.
        created_at: Timestamp of record creation.
    """

    __tablename__ = "recurring_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    match_key: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String(10), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    cancelled_at: Mapped[datetime.date | None] = mapped_column(
        Date, nullable=True, default=None
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[User] = relationship(back_populates="recurring_payments")
    category: Mapped[Category | None] = relationship()
    aliases: Mapped[list[RecurringPaymentAlias]] = relationship(
        back_populates="payment",
        cascade="all, delete-orphan",
        order_by="RecurringPaymentAlias.id",
    )


class RecurringPaymentAlias(Base):
    """A bank label merged into a classified recurring payment.

    When the bank or the merchant renames a debit, the debits under the other
    label are the same payment: each alias makes the tracking count them for
    the payment it belongs to.

    Attributes:
        id: Primary key.
        payment_id: The payment this label is merged into.
        match_key: Normalized bank label of the debits (encrypted at rest).
        amount: Reference amount under this label, in positive integer centimes.
        created_at: Timestamp of record creation.
    """

    __tablename__ = "recurring_payment_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(
        ForeignKey("recurring_payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_key: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    payment: Mapped[RecurringPayment] = relationship(back_populates="aliases")
