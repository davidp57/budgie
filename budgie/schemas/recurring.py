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
        cancelled_at: Cancellation date, when declared at classification.
    """

    key: str = Field(..., min_length=1, max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    amount: int = Field(..., gt=0)
    period: Period
    kind: RecurringKind
    cancelled_at: datetime.date | None = None


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


class RecurringAliasCreate(BaseModel):
    """A label to merge into a classified payment (from a candidate).

    Attributes:
        key: Normalized bank label of the candidate.
        amount: Reference amount under that label, in positive centimes.
    """

    key: str = Field(..., min_length=1, max_length=200)
    amount: int = Field(..., gt=0)


class RecurringMerge(BaseModel):
    """Merge another classified payment into this one.

    Attributes:
        other_id: The payment to absorb; it is deleted.
    """

    other_id: int


class RecurringAliasRead(BaseModel):
    """A bank label merged into a classified payment.

    Attributes:
        id: Primary key.
        key: Normalized bank label.
        amount: Reference amount under that label, in centimes.
    """

    id: int
    key: str
    amount: int


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
        aliases: Other bank labels merged into the payment.
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
    aliases: list[RecurringAliasRead]


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


class PriceSegmentRead(BaseModel):
    """A stretch of time billed at one price.

    Attributes:
        start: Date of the first debit at this price.
        end: Date of the last debit at this price.
        amount: Amount per period, in centimes.
        count: Number of debits in the stretch.
    """

    start: datetime.date
    end: datetime.date
    amount: int
    count: int


class RecurringLineRef(BaseModel):
    """Points at a service line: a classified payment, or a detected one.

    Attributes:
        payment_id: The classified payment, for a classified line.
        key: Normalized label, for a line not classified yet.
        amount: Current amount, for a line not classified yet.
        period: Billing rhythm, for a line not classified yet.
    """

    payment_id: int | None = None
    key: str | None = Field(None, min_length=1, max_length=200)
    amount: int | None = Field(None, gt=0)
    period: Period | None = None


class RecurringLine(BaseModel):
    """One service, as a person sees it: one line however its price changed.

    Attributes:
        id: Stable identifier of the line in this board.
        ref: How to point at the line in a link request.
        payment: The classified payment, when the line is classified.
        name: Display name (the payment's, or derived from the label).
        key: Normalized label of the latest debits.
        label: Latest raw bank label, when the line is not classified.
        period: Current billing rhythm.
        amount: Current amount per period, in centimes.
        monthly_cost: Current amount brought back to one month, in centimes.
        first_date: Date of the first debit.
        last_date: Date of the most recent debit.
        running: Debited within the last one and a half periods.
        likely_other: Not classified, and probably not a subscription (a
            transfer, or 100 €/month or more).
        segments: Stretches of one price, oldest first.
    """

    id: str
    ref: RecurringLineRef
    payment: RecurringPaymentRead | None
    name: str
    key: str
    label: str | None
    period: Period
    amount: int
    monthly_cost: int
    first_date: datetime.date | None
    last_date: datetime.date | None
    running: bool
    likely_other: bool
    segments: list[PriceSegmentRead]


class RecurringLinkSuggestion(BaseModel):
    """Two lines probably the same service under a new label.

    Attributes:
        earlier_id: The line that stopped.
        later_id: The line that started right after, at the exact same amount.
    """

    earlier_id: str
    later_id: str


class RecurringBoard(BaseModel):
    """Every service line, what runs now, and what it costs.

    Attributes:
        as_of: Reference date of "running" and of the statuses: the date of
            the most recent imported debit (today when there is none), so that
            statements imported weeks ago do not make everything look stopped.
        lines: Every line (dismissed ones included), most expensive first.
        monthly_total: Monthly cost of the running lines that are
            subscriptions, classified or not (unclassified lines that are
            probably not subscriptions left out), in centimes.
        yearly_total: ``monthly_total`` times twelve, in centimes.
        estimated_count: Running lines counted in the total without having
            been confirmed as subscriptions.
        attention_count: Classified subscriptions that need a look.
        refused_count: Link suggestions the user said no to (a reset forgets
            them).
        suggestions: Probable renames, at the exact same amount.
    """

    as_of: datetime.date
    lines: list[RecurringLine]
    monthly_total: int
    yearly_total: int
    estimated_count: int
    attention_count: int
    refused_count: int
    suggestions: list[RecurringLinkSuggestion]


class RecurringLink(BaseModel):
    """Link two service lines: the later one absorbs the earlier one.

    Attributes:
        earlier: The line to absorb.
        later: The line that stays (classified as a subscription if needed).
    """

    earlier: RecurringLineRef
    later: RecurringLineRef


class RecurringLinkRefuse(BaseModel):
    """Say no to a link suggestion between two lines.

    Attributes:
        earlier_key: Normalized label of the line that stopped.
        later_key: Normalized label of the line that followed.
    """

    earlier_key: str = Field(..., min_length=1, max_length=200)
    later_key: str = Field(..., min_length=1, max_length=200)
