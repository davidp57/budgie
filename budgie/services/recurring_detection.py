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
from collections.abc import Iterable, Sequence, Set
from dataclasses import dataclass, field


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
        hits: The debits of the series, oldest first.
    """

    key: str
    label: str
    amount: int
    period: Period
    occurrences: int
    first_date: datetime.date
    last_date: datetime.date
    hits: tuple[BankDebit, ...] = ()

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
            hits=tuple(debits),
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
    """One label of a payment the user has classified, as the tracking sees it.

    A payment carries its main label, plus one alias per label merged into it
    (after the bank or the merchant renamed the debit): each comes as its own
    ``TrackedPayment`` with the same ``id``.

    Attributes:
        id: Primary key of the payment.
        key: Normalized label.
        amount: Reference amount of this label, in positive integer centimes.
        period: Billing rhythm of the payment.
        alias_id: Id of the merged label, or None for the payment's main label.
    """

    id: int
    key: str
    amount: int
    period: Period
    alias_id: int | None = None


@dataclass
class PaymentTrack:
    """What the debits say about one classified payment.

    Attributes:
        dates: Dates of the debits attributed to the payment, oldest first.
        current_amount: Amount of the most recent attributed debit, or the
            reference amount when none was attributed.
        last_reference: Reference amount of the label that billed the most
            recent debit (a price change is measured against it), or None
            when no debit was attributed.
        last_alias_id: Merged label that billed the most recent debit, or
            None when it was the main label (or no debit was attributed).
        amounts: Amounts of the debits, in the order of ``dates``.
    """

    dates: list[datetime.date]
    current_amount: int
    last_reference: int | None = None
    last_alias_id: int | None = None
    amounts: list[int] = field(default_factory=list)

    @property
    def last_date(self) -> datetime.date | None:
        """Date of the most recent attributed debit."""
        return self.dates[-1] if self.dates else None


@dataclass
class _Entry:
    """Attribution state of one label of a payment."""

    label: TrackedPayment
    # Price the label is billed at: its reference amount, then the amount of
    # each confirmed price change.  Never the amount of any single debit, so
    # that a run of purchases cannot drift the tolerance step by step.
    price: int
    hits: list[BankDebit] = field(default_factory=list)


def track_payments(
    debits: Iterable[BankDebit], payments: Iterable[TrackedPayment]
) -> tuple[dict[int, PaymentTrack], list[BankDebit]]:
    """Attribute debits to the payments the user has classified.

    Each label of a payment (main or merged) is followed on its own.  Under a
    key that carries a single label, a debit outside the amount tolerance that
    falls one period after the previous attributed debit is a price change: it
    is attributed, and its amount becomes the current one; earlier debits at
    an older price are attributed the same way, walking back from the first
    attributed debit.  Under a key with several labels, a debit goes to the
    label of the nearest amount within tolerance.  Every other debit is left
    unattributed, to be searched for new candidates.

    Args:
        debits: Bank debits, in any order.
        payments: Labels of the classified payments, main and merged.

    Returns:
        The track of each payment by id, the debits of all its labels
        together, and the unattributed debits.
    """
    labels = list(payments)
    by_key: dict[str, list[_Entry]] = defaultdict(list)
    for label in labels:
        by_key[label.key].append(_Entry(label=label, price=label.amount))
    by_debit_key: dict[str, list[BankDebit]] = defaultdict(list)
    for debit in debits:
        by_debit_key[normalize_label(debit.label)].append(debit)

    unattributed: list[BankDebit] = []
    for key, key_debits in by_debit_key.items():
        key_debits.sort(key=lambda d: d.date)
        entries = by_key.get(key)
        if not entries:
            unattributed.extend(key_debits)
            continue
        for debit in key_debits:
            entry = _attribute(debit, entries, key_debits)
            if entry is None:
                unattributed.append(debit)
            else:
                entry.hits.append(debit)
    remaining = _extend_backwards(unattributed, by_key, by_debit_key)

    reference = {lab.id: lab.amount for lab in reversed(labels) if lab.alias_id is None}
    hits_by_payment: dict[int, list[tuple[BankDebit, TrackedPayment]]] = defaultdict(
        list
    )
    for entries in by_key.values():
        for entry in entries:
            hits_by_payment[entry.label.id].extend((h, entry.label) for h in entry.hits)
    tracks: dict[int, PaymentTrack] = {}
    for label in labels:
        if label.id in tracks:
            continue
        hits = sorted(hits_by_payment[label.id], key=lambda h: h[0].date)
        if hits:
            last_debit, last_label = hits[-1]
            tracks[label.id] = PaymentTrack(
                dates=[debit.date for debit, _ in hits],
                current_amount=last_debit.amount,
                last_reference=last_label.amount,
                last_alias_id=last_label.alias_id,
                amounts=[debit.amount for debit, _ in hits],
            )
        else:
            tracks[label.id] = PaymentTrack(
                dates=[], current_amount=reference.get(label.id, label.amount)
            )
    return tracks, remaining


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
    by_key: dict[str, list[_Entry]],
    by_debit_key: dict[str, list[BankDebit]],
) -> list[BankDebit]:
    """Attribute the older debits of a single label billed at an earlier price.

    Once the user accepts a new price, the reference amount no longer matches
    the debits made before the change, and the forward pass has no earlier
    debit to anchor them on.  Walking back from the first attributed debit, an
    earlier debit one period before it is attributed when it has the same
    amount, or when an older debit one period further back confirms its
    amount: an isolated purchase is never taken for an old price.

    Returns:
        The debits that are still unattributed, oldest first.
    """
    remaining: list[BankDebit] = []
    for debit in sorted(unattributed, key=lambda d: d.date, reverse=True):
        key = normalize_label(debit.label)
        entries = by_key.get(key)
        hit_entries = [e for e in entries or [] if e.hits]
        if entries and _one_payment(entries) and hit_entries:
            entry = min(hit_entries, key=lambda e: e.hits[0].date)
            first = entry.hits[0]
            period = entry.label.period
            if interval_matches((first.date - debit.date).days, period) and (
                amount_matches(debit.amount, first.amount)
                or _confirmed_elsewhere(debit, by_debit_key[key], period, later=False)
            ):
                entry.hits.insert(0, debit)
                continue
        remaining.append(debit)
    remaining.reverse()
    return remaining


def _attribute(
    debit: BankDebit, entries: list[_Entry], key_debits: list[BankDebit]
) -> _Entry | None:
    """Return the label entry a debit belongs to, or None.

    A debit within the tolerance of a label goes to the nearest one.  When
    every label under the key belongs to one payment, a debit outside the
    tolerance is a price change of the label that billed last, only when it
    falls one period after the last attributed debit, no debit at the current
    price fills that period, and a second debit of the new amount follows one
    period later.  A one-off purchase at the same
    merchant is left alone; a new price is followed from its second debit on.
    """
    matching = [
        e
        for e in entries
        if amount_matches(debit.amount, e.price)
        or amount_matches(debit.amount, e.label.amount)
    ]
    if matching:
        return min(
            matching,
            key=lambda e: min(
                abs(debit.amount - e.price), abs(debit.amount - e.label.amount)
            ),
        )
    if not _one_payment(entries):
        return None
    hit_entries = [e for e in entries if e.hits]
    if not hit_entries:
        return None
    latest = max(hit_entries, key=lambda e: e.hits[-1].date)
    last = latest.hits[-1].date
    period = latest.label.period
    if (
        interval_matches((debit.date - last).days, period)
        and not _regular_debit_in_window(last, latest.price, key_debits, period)
        and _confirmed_elsewhere(debit, key_debits, period, later=True)
    ):
        latest.price = debit.amount
        return latest
    return None


def _one_payment(entries: list[_Entry]) -> bool:
    """Tell whether every label under a key belongs to the same payment."""
    return len({e.label.id for e in entries}) == 1


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


# ---------------------------------------------------------------------------
# Service lines: what a person sees as one subscription over time
# ---------------------------------------------------------------------------

#: Successive series of one label belong to the same service when the next
#: one starts within this many periods after the previous one stopped.
CHAIN_GAP_PERIODS = 2


def is_running(last_date: datetime.date, period: Period, today: datetime.date) -> bool:
    """Tell whether a payment still runs: debited within the last 1.5 periods.

    Args:
        last_date: Date of the most recent debit.
        period: Billing rhythm.
        today: Reference date.

    Returns:
        True when the last debit is recent enough for the payment to go on.
    """
    return (today - last_date).days <= ENDED_AFTER_PERIODS * PERIOD_DAYS[period]


@dataclass(frozen=True)
class PriceSegment:
    """A stretch of time billed at one price.

    Attributes:
        start: Date of the first debit at this price.
        end: Date of the last debit at this price.
        amount: Median amount of the stretch, in positive integer centimes.
        count: Number of debits in the stretch.
    """

    start: datetime.date
    end: datetime.date
    amount: int
    count: int


def price_segments(hits: Sequence[tuple[datetime.date, int]]) -> list[PriceSegment]:
    """Cut a line's debits into stretches of one price.

    A new stretch starts when an amount leaves the tolerance of the first
    amount of the current stretch.

    Args:
        hits: ``(date, amount)`` of each debit, in any order.

    Returns:
        The stretches, oldest first.
    """
    segments: list[PriceSegment] = []
    current: list[tuple[datetime.date, int]] = []

    def close() -> None:
        if current:
            segments.append(
                PriceSegment(
                    start=current[0][0],
                    end=current[-1][0],
                    amount=round(statistics.median(a for _, a in current)),
                    count=len(current),
                )
            )

    for date, amount in sorted(hits):
        if current and not amount_matches(amount, current[0][1]):
            close()
            current = []
        current.append((date, amount))
    close()
    return segments


@dataclass(frozen=True)
class SeriesChain:
    """Successive series of one label: one service whose price changed.

    Attributes:
        key: Normalized label of the series.
        series: The series, oldest first; they never overlap in time.
    """

    key: str
    series: tuple[RecurringSeries, ...]

    @property
    def latest(self) -> RecurringSeries:
        """The most recent series: its price and rhythm are the current ones."""
        return self.series[-1]

    @property
    def amount(self) -> int:
        """Current amount per period, in centimes."""
        return self.latest.amount

    @property
    def period(self) -> Period:
        """Current billing rhythm."""
        return self.latest.period

    @property
    def first_date(self) -> datetime.date:
        """Date of the first debit of the service."""
        return self.series[0].first_date

    @property
    def last_date(self) -> datetime.date:
        """Date of the most recent debit of the service."""
        return self.latest.last_date

    @property
    def hits(self) -> list[BankDebit]:
        """Every debit of the service, oldest first."""
        return sorted((h for s in self.series for h in s.hits), key=lambda d: d.date)


def chain_series(series: Iterable[RecurringSeries]) -> list[SeriesChain]:
    """Group the series of each label into service lines.

    Series of one label that follow each other (the next starts after the
    previous stopped, within :data:`CHAIN_GAP_PERIODS` periods) are one
    service whose price changed; series that overlap in time are distinct
    services billed by the same merchant (two formulas).

    Args:
        series: Detected series, in any order.

    Returns:
        The service lines, most expensive per month first.
    """
    by_key: dict[str, list[RecurringSeries]] = defaultdict(list)
    for s in series:
        by_key[s.key].append(s)
    chains: list[list[RecurringSeries]] = []
    for group in by_key.values():
        open_chains: list[list[RecurringSeries]] = []
        for s in sorted(group, key=lambda s: s.first_date):
            followers = [
                c
                for c in open_chains
                if c[-1].last_date < s.first_date
                and (s.first_date - c[-1].last_date).days
                <= CHAIN_GAP_PERIODS * PERIOD_DAYS[c[-1].period]
            ]
            if followers:
                max(followers, key=lambda c: c[-1].last_date).append(s)
            else:
                open_chains.append([s])
        chains.extend(open_chains)
    result = [SeriesChain(key=c[0].key, series=tuple(c)) for c in chains]
    result.sort(key=lambda c: (-c.latest.monthly_cost, c.key))
    return result


@dataclass(frozen=True)
class LineSpan:
    """What link suggestions need to know about a service line.

    Attributes:
        id: Identifier of the line.
        key: Normalized label of the line's latest debits.
        first_date: Date of the line's first debit.
        last_date: Date of the line's most recent debit.
        first_amount: Amount of the line's first price stretch, in centimes.
        last_amount: Amount of the line's latest price stretch, in centimes.
        period: Billing rhythm.
    """

    id: str
    key: str
    first_date: datetime.date
    last_date: datetime.date
    first_amount: int
    last_amount: int
    period: Period


def suggest_links(
    spans: Iterable[LineSpan],
    refused: Set[tuple[str, str]] = frozenset(),
) -> list[tuple[str, str]]:
    """Suggest the lines that are probably one service under a new label.

    A line that stops, then another of a different label that starts within
    :data:`CHAIN_GAP_PERIODS` periods, at the **exact same** amount.  Measured
    on a real export: with a tolerance on the amount, 12 suggestions out of 13
    were coincidences; the exact amount kept only the genuine renames.

    A refused pair is left out before lines are paired, so that it does not
    take the place of another possible pair (the right successor of another
    line, or the next successor of the same one).

    Args:
        spans: The service lines.
        refused: ``(earlier key, later key)`` pairs the user said no to.

    Returns:
        ``(earlier line id, later line id)`` pairs, oldest first; each line is
        the earlier one of at most one pair and the later one of at most one.
    """
    ordered = sorted(spans, key=lambda s: s.first_date)
    taken_as_later: set[str] = set()
    links: list[tuple[str, str]] = []
    for earlier in sorted(ordered, key=lambda s: s.last_date):
        successors = [
            later
            for later in ordered
            if later.id != earlier.id
            and later.id not in taken_as_later
            and later.key != earlier.key
            and later.first_date > earlier.last_date
            and (later.first_date - earlier.last_date).days
            <= CHAIN_GAP_PERIODS * PERIOD_DAYS[earlier.period]
            and later.first_amount == earlier.last_amount
            and (earlier.key, later.key) not in refused
        ]
        if successors:
            later = min(successors, key=lambda s: s.first_date)
            taken_as_later.add(later.id)
            links.append((earlier.id, later.id))
    return links
