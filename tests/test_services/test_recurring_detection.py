"""Tests for the pure recurring-payment detection engine."""

from __future__ import annotations

import datetime

from budgie.services.recurring_detection import (
    BankDebit,
    PaymentStatus,
    PaymentTrack,
    Period,
    TrackedPayment,
    debits_after_cancellation,
    detect_series,
    monthly_cost,
    normalize_label,
    payment_status,
    track_payments,
)


def _monthly(
    label: str,
    amount: int,
    count: int,
    start: datetime.date = datetime.date(2025, 1, 5),
    step_days: int = 30,
) -> list[BankDebit]:
    return [
        BankDebit(
            date=start + datetime.timedelta(days=step_days * i),
            amount=amount,
            label=label,
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# normalize_label
# ---------------------------------------------------------------------------


def test_card_payments_of_different_days_share_one_key() -> None:
    a = normalize_label("CARTE 26/02/26 STREAMFLIX.COM CB*6338")
    b = normalize_label("CARTE 27/01/26 STREAMFLIX.COM CB*6338")
    assert a == b == "STREAMFLIX COM"


def test_direct_debit_prefix_is_removed() -> None:
    assert normalize_label("PRLV SEPA OPERATEUR TELECOM") == "OPERATEUR TELECOM"


def test_digits_and_references_are_removed() -> None:
    assert normalize_label("PRLV SEPA ASSUR 0042 REF 9981") == "ASSUR REF"


def test_case_and_accents_do_not_split_keys() -> None:
    assert normalize_label("carte 01/02/26 Café du Coin") == normalize_label(
        "CARTE 03/03/26 CAFE DU COIN"
    )


# ---------------------------------------------------------------------------
# detect_series
# ---------------------------------------------------------------------------


def test_monthly_series_is_detected() -> None:
    debits = _monthly("CARTE 05/01/25 STREAMFLIX CB*1", 1399, 6)
    [series] = detect_series(debits)
    assert series.key == "STREAMFLIX"
    assert series.period is Period.MONTHLY
    assert series.amount == 1399
    assert series.occurrences == 6
    assert series.last_date == debits[-1].date


def test_quarterly_series_is_detected() -> None:
    debits = _monthly("PRLV SEPA EAU", 4500, 4, step_days=91)
    [series] = detect_series(debits)
    assert series.period is Period.QUARTERLY


def test_yearly_series_needs_only_two_occurrences() -> None:
    debits = _monthly("PRLV SEPA ANTIVIRUS", 5999, 2, step_days=365)
    [series] = detect_series(debits)
    assert series.period is Period.YEARLY


def test_a_short_series_must_repeat_the_exact_amount() -> None:
    start = datetime.date(2024, 7, 1)
    debits = [
        BankDebit(date=start, amount=4670, label="CARTE SUPERMARCHE"),
        BankDebit(
            date=start + datetime.timedelta(days=366),
            amount=4590,
            label="CARTE SUPERMARCHE",
        ),
    ]
    assert detect_series(debits) == []


def test_two_monthly_occurrences_are_not_enough() -> None:
    assert detect_series(_monthly("PRLV SEPA GYM", 2990, 2)) == []


def test_irregular_intervals_are_rejected() -> None:
    start = datetime.date(2025, 1, 1)
    debits = [
        BankDebit(date=start + datetime.timedelta(days=d), amount=1500, label="SHOP")
        for d in (0, 9, 50, 61, 140, 150)
    ]
    assert detect_series(debits) == []


def test_two_amounts_under_one_label_give_two_series() -> None:
    debits = _monthly("APPSTORE BILL", 299, 5) + _monthly("APPSTORE BILL", 999, 5)
    series = detect_series(debits)
    assert sorted(s.amount for s in series) == [299, 999]
    assert {s.key for s in series} == {"APPSTORE BILL"}


def test_small_price_variations_stay_in_one_series() -> None:
    debits = _monthly("PRLV SEPA ENERGIE", 8000, 6)
    debits[3] = BankDebit(date=debits[3].date, amount=8400, label=debits[3].label)
    [series] = detect_series(debits)
    assert series.occurrences == 6


def test_one_off_purchases_do_not_disturb_a_series() -> None:
    debits = [
        *_monthly("STREAMFLIX", 1399, 6),
        BankDebit(date=datetime.date(2025, 2, 14), amount=4999, label="STREAMFLIX"),
    ]
    [series] = detect_series(debits)
    assert series.amount == 1399


def test_series_are_sorted_by_monthly_cost() -> None:
    debits = _monthly("SMALL", 199, 4) + _monthly("BIG", 4999, 4)
    assert [s.key for s in detect_series(debits)] == ["BIG", "SMALL"]


# ---------------------------------------------------------------------------
# monthly_cost
# ---------------------------------------------------------------------------


def test_monthly_cost_of_each_period() -> None:
    assert monthly_cost(1200, Period.MONTHLY) == 1200
    assert monthly_cost(3000, Period.QUARTERLY) == 1000
    assert monthly_cost(12000, Period.YEARLY) == 1000


def test_monthly_cost_is_rounded_to_whole_centimes() -> None:
    assert monthly_cost(5999, Period.YEARLY) == 500


# ---------------------------------------------------------------------------
# track_payments, payment_status, debits_after_cancellation
# ---------------------------------------------------------------------------


def _payment(pid: int, key: str, amount: int) -> TrackedPayment:
    return TrackedPayment(id=pid, key=key, amount=amount, period=Period.MONTHLY)


def test_debits_of_a_classified_payment_are_attributed() -> None:
    debits = _monthly("CARTE 05/01/25 STREAMFLIX CB*1", 1399, 4)
    tracks, rest = track_payments(debits, [_payment(1, "STREAMFLIX", 1399)])
    assert rest == []
    assert tracks[1].dates == [d.date for d in debits]
    assert tracks[1].current_amount == 1399


def test_a_price_increase_on_time_is_followed() -> None:
    debits = _monthly("STREAMFLIX", 1399, 3) + _monthly(
        "STREAMFLIX", 1599, 3, start=datetime.date(2025, 4, 5)
    )
    tracks, rest = track_payments(debits, [_payment(1, "STREAMFLIX", 1399)])
    assert rest == []
    assert tracks[1].current_amount == 1599
    assert len(tracks[1].dates) == 6


def test_an_off_time_purchase_is_not_a_price_change() -> None:
    debits = [
        *_monthly("STREAMFLIX", 1399, 3),
        BankDebit(date=datetime.date(2025, 2, 20), amount=4999, label="STREAMFLIX"),
    ]
    tracks, rest = track_payments(debits, [_payment(1, "STREAMFLIX", 1399)])
    assert [d.amount for d in rest] == [4999]
    assert tracks[1].current_amount == 1399


def test_under_a_key_with_two_payments_a_new_amount_stays_a_candidate() -> None:
    debits = (
        _monthly("APPSTORE BILL", 299, 4)
        + _monthly("APPSTORE BILL", 999, 4)
        + _monthly("APPSTORE BILL", 1999, 4, start=datetime.date(2025, 1, 9))
    )
    payments = [_payment(1, "APPSTORE BILL", 299), _payment(2, "APPSTORE BILL", 999)]
    tracks, rest = track_payments(debits, payments)
    assert len(tracks[1].dates) == len(tracks[2].dates) == 4
    [series] = detect_series(rest)
    assert series.amount == 1999


def test_other_keys_are_left_unattributed() -> None:
    debits = _monthly("GYM", 2990, 4)
    tracks, rest = track_payments(debits, [_payment(1, "STREAMFLIX", 1399)])
    assert tracks[1].dates == []
    assert len(rest) == 4


def test_status_active_ended_cancelled() -> None:
    track = PaymentTrack(dates=[datetime.date(2025, 6, 1)], current_amount=1399)
    assert (
        payment_status(track, Period.MONTHLY, None, datetime.date(2025, 7, 1))
        is PaymentStatus.ACTIVE
    )
    assert (
        payment_status(track, Period.MONTHLY, None, datetime.date(2025, 7, 20))
        is PaymentStatus.PROBABLY_ENDED
    )
    assert (
        payment_status(
            track, Period.MONTHLY, datetime.date(2025, 6, 2), datetime.date(2025, 7, 1)
        )
        is PaymentStatus.CANCELLED
    )


def test_a_yearly_payment_is_not_ended_after_a_few_months() -> None:
    track = PaymentTrack(dates=[datetime.date(2025, 1, 1)], current_amount=5999)
    assert (
        payment_status(track, Period.YEARLY, None, datetime.date(2025, 9, 1))
        is PaymentStatus.ACTIVE
    )


def test_debits_after_a_cancellation_are_reported() -> None:
    track = PaymentTrack(
        dates=[
            datetime.date(2025, 5, 5),
            datetime.date(2025, 6, 5),
            datetime.date(2025, 7, 5),
        ],
        current_amount=1399,
    )
    assert debits_after_cancellation(track, datetime.date(2025, 6, 1)) == [
        datetime.date(2025, 6, 5),
        datetime.date(2025, 7, 5),
    ]
    assert debits_after_cancellation(track, None) == []


def test_an_accepted_new_price_keeps_the_older_debits() -> None:
    debits = _monthly("STREAMFLIX", 1399, 3) + _monthly(
        "STREAMFLIX", 1599, 3, start=datetime.date(2025, 4, 5)
    )
    tracks, rest = track_payments(debits, [_payment(1, "STREAMFLIX", 1599)])
    assert rest == []
    assert len(tracks[1].dates) == 6
    assert tracks[1].dates == sorted(tracks[1].dates)
    assert tracks[1].current_amount == 1599


def test_normalizing_a_key_again_keeps_it() -> None:
    labels = [
        "PRLV SEPA CARTE NOIRE ABONNEMENT CAFE",
        "PRLV SEPA PRLV SEPA FOO BAR",
        "CARTE 01/02/26 SUPER LONG MERCHANT NAME WITH MANY WORDS X Y AND MORE",
        "CARTE 05/01/25 STREAMFLIX.COM CB*1",
    ]
    for label in labels:
        key = normalize_label(label)
        assert normalize_label(key) == key, label
        assert len(key) <= 40


def test_a_one_off_purchase_on_time_is_not_a_price_change() -> None:
    debits = [
        *_monthly("AMAZON PRIME", 699, 3),
        BankDebit(date=datetime.date(2025, 4, 3), amount=4590, label="AMAZON PRIME"),
    ]
    tracks, rest = track_payments(debits, [_payment(1, "AMAZON PRIME", 699)])
    assert tracks[1].current_amount == 699
    assert len(tracks[1].dates) == 3
    assert [d.amount for d in rest] == [4590]


def test_a_purchase_next_to_the_regular_debit_is_not_attributed() -> None:
    debits = [
        *_monthly("AMAZON PRIME", 699, 4),
        BankDebit(date=datetime.date(2025, 3, 3), amount=4590, label="AMAZON PRIME"),
        BankDebit(date=datetime.date(2025, 4, 2), amount=4590, label="AMAZON PRIME"),
    ]
    tracks, rest = track_payments(debits, [_payment(1, "AMAZON PRIME", 699)])
    assert len(tracks[1].dates) == 4
    assert tracks[1].current_amount == 699
    assert len(rest) == 2


def test_the_tolerance_does_not_follow_an_isolated_debit() -> None:
    start = datetime.date(2025, 1, 1)
    amounts = [5000, 5450, 5900, 5000]
    debits = [
        BankDebit(date=start + datetime.timedelta(days=30 * i), amount=a, label="SHOP")
        for i, a in enumerate(amounts)
    ]
    tracks, rest = track_payments(debits, [_payment(1, "SHOP", 5000)])
    assert [d.amount for d in rest] == [5900]
    assert len(tracks[1].dates) == 3
