"""Pure detection of recurring bank debits (subscriptions and the like).

Works on plain values, with no database access, so that the thresholds can be
tested on constructed series.  The thresholds were measured on a real bank
export of 26 months (one checking account): they are named constants to be
revisited on other histories.
"""

from __future__ import annotations

import datetime
import enum
import itertools
import re
import statistics
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass


class Period(enum.StrEnum):
    """Billing rhythm of a recurring payment."""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


#: Average length of each period, in days.
PERIOD_DAYS: dict[Period, float] = {
    Period.MONTHLY: 365.25 / 12,
    Period.QUARTERLY: 365.25 / 4,
    Period.YEARLY: 365.25,
}

#: Number of months covered by one payment of each period.
PERIOD_MONTHS: dict[Period, int] = {
    Period.MONTHLY: 1,
    Period.QUARTERLY: 3,
    Period.YEARLY: 12,
}

#: An interval matches a period when it is within this share of its length.
INTERVAL_TOLERANCE = 0.15

#: Amounts within this share of a reference amount belong to the same payment.
AMOUNT_TOLERANCE = 0.10

#: Share of intervals of a series that must match its period.
MIN_REGULAR_SHARE = 0.6

#: Fewest occurrences for a series to count.  Two yearly payments already
#: need two years of history; asking three found none on 26 months.
MIN_OCCURRENCES: dict[Period, int] = {
    Period.MONTHLY: 3,
    Period.QUARTERLY: 3,
    Period.YEARLY: 2,
}

#: A series shorter than this must repeat the exact same amount.  Two or
#: three purchases in the same shop at the right interval are common; a
#: subscription bills the same price to the centime.  Measured: without this
#: rule, 2-occurrence yearly series were mostly grocery and restaurant pairs.
STRICT_SERIES_LENGTH = 4

#: Longest key kept, in characters (whole words only).
MAX_KEY_LENGTH = 40

_PREFIXES = re.compile(r"^(CARTE|PRLV SEPA|PRLV|VIR SEPA|VIR|AVOIR|PAIEMENT CB)\s+")
_DATES = re.compile(r"\d{2}/\d{2}(/\d{2,4})?")
_CARD_NUMBERS = re.compile(r"CB\*\d+")
_NON_LETTERS = re.compile(r"[^A-Z ]")


@dataclass(frozen=True)
class BankDebit:
    """One bank debit, as the detection sees it.

    Attributes:
        date: Date of the debit.
        amount: Debited amount, in positive integer centimes.
        label: Decrypted bank label of the transaction.
    """

    date: datetime.date
    amount: int
    label: str


@dataclass(frozen=True)
class RecurringSeries:
    """A recurring payment found in the debits.

    Attributes:
        key: Normalized label shared by the debits.
        label: Most recent raw label of the series.
        amount: Median amount, in positive integer centimes.
        period: Billing rhythm.
        occurrences: Number of debits in the series.
        first_date: Date of the first debit.
        last_date: Date of the most recent debit.
    """

    key: str
    label: str
    amount: int
    period: Period
    occurrences: int
    first_date: datetime.date
    last_date: datetime.date

    @property
    def monthly_cost(self) -> int:
        """Amount brought back to one month, in centimes."""
        return monthly_cost(self.amount, self.period)


def normalize_label(label: str) -> str:
    """Reduce a bank label to a key shared by every debit of one payee.

    Removes the operation prefixes (card, direct debit, transfer), dates, card
    numbers, digits, accents and punctuation, and keeps whole words up to
    :data:`MAX_KEY_LENGTH` characters.  Normalizing a key again returns the
    same key, so that a stored key keeps matching the labels it came from.

    Args:
        label: Raw bank label.

    Returns:
        Upper-case key of letters and single spaces.
    """
    text = unicodedata.normalize("NFKD", label.upper())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _DATES.sub(" ", text)
    text = _CARD_NUMBERS.sub(" ", text)
    text = " ".join(_NON_LETTERS.sub(" ", text).split())
    stripped = _PREFIXES.sub("", text)
    while stripped != text:  # "PRLV SEPA PRLV SEPA X", "PRLV SEPA CARTE X"
        text, stripped = stripped, _PREFIXES.sub("", stripped)
    key = ""
    for word in text.split():
        if len(word) < 2:
            continue
        longer = f"{key} {word}" if key else word
        if len(longer) > MAX_KEY_LENGTH:
            break
        key = longer
    return key


def monthly_cost(amount: int, period: Period) -> int:
    """Bring an amount paid once per period back to one month.

    Args:
        amount: Amount per period, in integer centimes.
        period: Billing rhythm.

    Returns:
        Amount per month, rounded to whole centimes.
    """
    return round(amount / PERIOD_MONTHS[period])


def amount_matches(amount: int, reference: int) -> bool:
    """Tell whether an amount belongs to the payment of a reference amount.

    Args:
        amount: Amount to test, in centimes.
        reference: Reference amount, in centimes.

    Returns:
        True when the amount is within :data:`AMOUNT_TOLERANCE` of the reference.
    """
    return abs(amount - reference) <= AMOUNT_TOLERANCE * abs(reference)


def interval_matches(days: float, period: Period) -> bool:
    """Tell whether an interval between two debits fits a period.

    Args:
        days: Interval in days.
        period: Billing rhythm.

    Returns:
        True when the interval is within :data:`INTERVAL_TOLERANCE` of the period.
    """
    length = PERIOD_DAYS[period]
    return abs(days - length) <= INTERVAL_TOLERANCE * length


def _amount_clusters(debits: list[BankDebit]) -> list[list[BankDebit]]:
    """Split debits into groups of close amounts, anchored on the smallest."""
    clusters: list[list[BankDebit]] = []
    for debit in sorted(debits, key=lambda d: d.amount):
        if clusters and amount_matches(debit.amount, clusters[-1][0].amount):
            clusters[-1].append(debit)
        else:
            clusters.append([debit])
    return clusters


def _series_of(key: str, debits: list[BankDebit]) -> RecurringSeries | None:
    """Return the series formed by close-amount debits, or None if irregular."""
    debits = sorted(debits, key=lambda d: d.date)
    if len(debits) < min(MIN_OCCURRENCES.values()):
        return None
    if len(debits) < STRICT_SERIES_LENGTH and len({d.amount for d in debits}) > 1:
        return None
    gaps = [(b.date - a.date).days for a, b in itertools.pairwise(debits)]
    median_gap = statistics.median(gaps)
    for period in Period:
        if not interval_matches(median_gap, period):
            continue
        if len(debits) < MIN_OCCURRENCES[period]:
            return None
        regular = sum(interval_matches(g, period) for g in gaps)
        if regular / len(gaps) < MIN_REGULAR_SHARE:
            return None
        return RecurringSeries(
            key=key,
            label=debits[-1].label,
            amount=round(statistics.median(d.amount for d in debits)),
            period=period,
            occurrences=len(debits),
            first_date=debits[0].date,
            last_date=debits[-1].date,
        )
    return None


def detect_series(debits: Iterable[BankDebit]) -> list[RecurringSeries]:
    """Find the recurring payments among bank debits.

    Debits are grouped by normalized label, then by close amount: a merchant
    that bills two subscriptions of different prices gives two series.

    Args:
        debits: Bank debits, in any order.

    Returns:
        The series found, most expensive per month first.
    """
    by_key: dict[str, list[BankDebit]] = defaultdict(list)
    for debit in debits:
        key = normalize_label(debit.label)
        if key:
            by_key[key].append(debit)

    found: list[RecurringSeries] = []
    for key, group in by_key.items():
        for cluster in _amount_clusters(group):
            series = _series_of(key, cluster)
            if series is not None:
                found.append(series)
    found.sort(key=lambda s: (-s.monthly_cost, s.key))
    return found


# ---------------------------------------------------------------------------
# Following payments the user has classified
# ---------------------------------------------------------------------------

#: A payment is probably over when nothing was debited for this many periods.
ENDED_AFTER_PERIODS = 1.5


class PaymentStatus(enum.StrEnum):
    """Computed state of a classified recurring payment."""

    ACTIVE = "active"
    PROBABLY_ENDED = "probably_ended"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TrackedPayment:
    """A payment the user has classified, as the tracking sees it.

    Attributes:
        id: Primary key of the payment.
        key: Normalized label the payment was classified under.
        amount: Reference amount, in positive integer centimes.
        period: Billing rhythm.
    """

    id: int
    key: str
    amount: int
    period: Period


@dataclass
class PaymentTrack:
    """What the debits say about one classified payment.

    Attributes:
        dates: Dates of the debits attributed to the payment, oldest first.
        current_amount: Amount of the most recent attributed debit, or the
            reference amount when none was attributed.
    """

    dates: list[datetime.date]
    current_amount: int

    @property
    def last_date(self) -> datetime.date | None:
        """Date of the most recent attributed debit."""
        return self.dates[-1] if self.dates else None


def track_payments(
    debits: Iterable[BankDebit], payments: Iterable[TrackedPayment]
) -> tuple[dict[int, PaymentTrack], list[BankDebit]]:
    """Attribute debits to the payments the user has classified.

    Under a key that carries a single classified payment, a debit outside the
    amount tolerance that falls one period after the previous attributed debit
    is a price change: it is attributed, and its amount becomes the current
    one; earlier debits at an older price are attributed the same way, walking
    back from the first attributed debit.  Under a key with several payments,
    a debit goes to the payment of the nearest amount within tolerance.  Every
    other debit is left unattributed, to be searched for new candidates.

    Args:
        debits: Bank debits, in any order.
        payments: Classified payments.

    Returns:
        The track of each payment by id, and the unattributed debits.
    """
    by_key: dict[str, list[TrackedPayment]] = defaultdict(list)
    for payment in payments:
        by_key[payment.key].append(payment)
    tracks = {
        p.id: PaymentTrack(dates=[], current_amount=p.amount)
        for group in by_key.values()
        for p in group
    }
    # Price each payment is billed at: the reference amount, then the amount
    # of each confirmed price change.  Never the amount of any single debit,
    # so that a run of purchases cannot drift the tolerance step by step.
    prices = {pid: track.current_amount for pid, track in tracks.items()}
    by_debit_key: dict[str, list[BankDebit]] = defaultdict(list)
    for debit in debits:
        by_debit_key[normalize_label(debit.label)].append(debit)

    unattributed: list[BankDebit] = []
    for key, key_debits in by_debit_key.items():
        key_debits.sort(key=lambda d: d.date)
        candidates = by_key.get(key)
        if not candidates:
            unattributed.extend(key_debits)
            continue
        for debit in key_debits:
            target = _attribute(debit, candidates, tracks, prices, key_debits)
            if target is None:
                unattributed.append(debit)
                continue
            track = tracks[target]
            track.dates.append(debit.date)
            track.current_amount = debit.amount
    return tracks, _extend_backwards(unattributed, by_key, tracks, by_debit_key)


def _confirmed_elsewhere(
    debit: BankDebit, key_debits: list[BankDebit], period: Period, *, later: bool
) -> bool:
    """Tell whether another debit of the same amount comes one period away."""
    for other in key_debits:
        days = (other.date - debit.date).days
        if not later:
            days = -days
        if (
            days > 0
            and interval_matches(days, period)
            and amount_matches(other.amount, debit.amount)
        ):
            return True
    return False


def _regular_debit_in_window(
    last: datetime.date, price: int, key_debits: list[BankDebit], period: Period
) -> bool:
    """Tell whether a debit at the expected price falls one period after *last*."""
    return any(
        amount_matches(d.amount, price)
        and interval_matches((d.date - last).days, period)
        for d in key_debits
    )


def _extend_backwards(
    unattributed: list[BankDebit],
    by_key: dict[str, list[TrackedPayment]],
    tracks: dict[int, PaymentTrack],
    by_debit_key: dict[str, list[BankDebit]],
) -> list[BankDebit]:
    """Attribute the older debits of a single payment billed at an earlier price.

    Once the user accepts a new price, the reference amount no longer matches
    the debits made before the change, and the forward pass has no earlier
    debit to anchor them on.  Walking back from the first attributed debit, an
    earlier debit one period before it is attributed when it has the same
    amount, or when an older debit one period further back confirms its
    amount: an isolated purchase is never taken for an old price.

    Returns:
        The debits that are still unattributed, oldest first.
    """
    amount_on: dict[tuple[str, datetime.date], int] = {
        (key, d.date): d.amount for key, group in by_debit_key.items() for d in group
    }
    anchors: dict[int, int] = {}
    remaining: list[BankDebit] = []
    for debit in sorted(unattributed, key=lambda d: d.date, reverse=True):
        key = normalize_label(debit.label)
        candidates = by_key.get(key)
        if candidates is not None and len(candidates) == 1:
            payment = candidates[0]
            track = tracks[payment.id]
            first = track.dates[0] if track.dates else None
            if first is not None and interval_matches(
                (first - debit.date).days, payment.period
            ):
                anchor = anchors.get(payment.id, amount_on.get((key, first), 0))
                if amount_matches(debit.amount, anchor) or _confirmed_elsewhere(
                    debit, by_debit_key[key], payment.period, later=False
                ):
                    track.dates.insert(0, debit.date)
                    anchors[payment.id] = debit.amount
                    continue
        remaining.append(debit)
    remaining.reverse()
    return remaining


def _attribute(
    debit: BankDebit,
    candidates: list[TrackedPayment],
    tracks: dict[int, PaymentTrack],
    prices: dict[int, int],
    key_debits: list[BankDebit],
) -> int | None:
    """Return the id of the payment a debit belongs to, or None.

    Under a single payment, a debit outside the price tolerance is a price
    change only when it falls one period after the last attributed debit, no
    debit at the current price fills that period, and a second debit of the
    new amount follows one period later.  A one-off purchase at the same
    merchant is left alone; a new price is followed from its second debit on.
    """
    if len(candidates) == 1:
        payment = candidates[0]
        price = prices[payment.id]
        if amount_matches(debit.amount, price) or amount_matches(
            debit.amount, payment.amount
        ):
            return payment.id
        last = tracks[payment.id].last_date
        if (
            last is not None
            and interval_matches((debit.date - last).days, payment.period)
            and not _regular_debit_in_window(last, price, key_debits, payment.period)
            and _confirmed_elsewhere(debit, key_debits, payment.period, later=True)
        ):
            prices[payment.id] = debit.amount
            return payment.id
        return None
    matching = [
        p
        for p in candidates
        if amount_matches(debit.amount, prices[p.id])
        or amount_matches(debit.amount, p.amount)
    ]
    if not matching:
        return None
    return min(matching, key=lambda p: abs(debit.amount - p.amount)).id


def payment_status(
    track: PaymentTrack,
    period: Period,
    cancelled_at: datetime.date | None,
    today: datetime.date,
) -> PaymentStatus:
    """Compute the state of a classified payment.

    Args:
        track: What the debits say about the payment.
        period: Billing rhythm.
        cancelled_at: Cancellation date declared by the user, if any.
        today: Reference date.

    Returns:
        Cancelled when a cancellation is declared; probably ended when nothing
        was debited for :data:`ENDED_AFTER_PERIODS` periods; active otherwise.
    """
    if cancelled_at is not None:
        return PaymentStatus.CANCELLED
    last = track.last_date
    if (
        last is not None
        and (today - last).days > ENDED_AFTER_PERIODS * PERIOD_DAYS[period]
    ):
        return PaymentStatus.PROBABLY_ENDED
    return PaymentStatus.ACTIVE


def debits_after_cancellation(
    track: PaymentTrack, cancelled_at: datetime.date | None
) -> list[datetime.date]:
    """Return the dates of debits attributed after a declared cancellation.

    Args:
        track: What the debits say about the payment.
        cancelled_at: Cancellation date declared by the user, if any.

    Returns:
        Dates strictly after the cancellation, oldest first.
    """
    if cancelled_at is None:
        return []
    return [d for d in track.dates if d > cancelled_at]
