"""Pydantic schemas for recurring payments (subscriptions and the like)."""

import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from budgie.services.recurring_detection import PaymentStatus, Period


class RecurringKind(StrEnum):
    """How the user classified a recurring payment."""

    SUBSCRIPTION = "subscription"
    OTHER = "other"
    DISMISSED = "dismissed"


class RecurringCandidateRead(BaseModel):
    """A recurring payment found in the bank debits, not classified yet.

    Attributes:
        key: Normalized bank label shared by the debits.
        label: Most recent raw bank label.
        amount: Median amount per period, in positive centimes.
        period: Billing rhythm.
        monthly_cost: Amount brought back to one month, in centimes.
        occurrences: Number of debits found.
        first_date: Date of the first debit.
        last_date: Date of the most recent debit.
    """

    key: str
    label: str
    amount: int
    period: Period
    monthly_cost: int
    occurrences: int
    first_date: datetime.date
    last_date: datetime.date


class RecurringPaymentCreate(BaseModel):
    """The user's verdict on a candidate.

    Attributes:
        key: Normalized bank label of the candidate.
        name: Display name.
        amount: Reference amount per period, in positive centimes.
        period: Billing rhythm.
        kind: Subscription, other recurring payment, or dismissed.
    """

    key: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    amount: int = Field(..., gt=0)
    period: Period
    kind: RecurringKind


class RecurringPaymentUpdate(BaseModel):
    """Partial update of a classified payment.

    Only the fields sent are changed; send ``cancelled_at`` or ``category_id``
    as ``null`` to clear them.

    Attributes:
        name: New display name.
        kind: New classification.
        amount: New reference amount (accepts a price change).
        category_id: Category, or null to clear it.
        cancelled_at: Cancellation date, or null to clear it.
    """

    name: str | None = Field(None, min_length=1, max_length=200)
    kind: RecurringKind | None = None
    amount: int | None = Field(None, gt=0)
    category_id: int | None = None
    cancelled_at: datetime.date | None = None


class RecurringPaymentRead(BaseModel):
    """A classified payment with what the debits say about it.

    Attributes:
        id: Primary key.
        key: Normalized bank label.
        name: Display name.
        kind: Classification.
        period: Billing rhythm.
        amount: Reference amount per period, in centimes.
        current_amount: Amount of the most recent debit, in centimes.
        monthly_cost: Current amount brought back to one month, in centimes.
        category_id: Category, if any.
        cancelled_at: Declared cancellation date, if any.
        last_date: Date of the most recent debit, if any.
        occurrences: Number of debits attributed.
        status: Active, probably ended, or cancelled.
        price_changed: True when the current amount left the tolerance of the
            reference amount.
        debits_after_cancellation: Debit dates after the declared cancellation.
    """

    id: int
    key: str
    name: str
    kind: RecurringKind
    period: Period
    amount: int
    current_amount: int
    monthly_cost: int
    category_id: int | None
    cancelled_at: datetime.date | None
    last_date: datetime.date | None
    occurrences: int
    status: PaymentStatus
    price_changed: bool
    debits_after_cancellation: list[datetime.date]


class RecurringOverview(BaseModel):
    """Every classified payment and what the subscriptions cost.

    Attributes:
        payments: Classified payments, dismissed ones included.
        monthly_total: Monthly cost of the active subscriptions, in centimes.
        yearly_total: ``monthly_total`` times twelve, in centimes.
        attention_count: Subscriptions that need a look (probably ended,
            debited after cancellation, or price changed).
    """

    payments: list[RecurringPaymentRead]
    monthly_total: int
    yearly_total: int
    attention_count: int
