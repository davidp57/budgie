"""Tests for service lines: chains of series, price segments, running, links."""

from __future__ import annotations

import datetime

from budgie.services.recurring_detection import (
    BankDebit,
    LineSpan,
    Period,
    chain_series,
    detect_series,
    is_running,
    price_segments,
    suggest_links,
)


def _monthly(
    label: str, amount: int, count: int, start: datetime.date
) -> list[BankDebit]:
    return [
        BankDebit(
            date=start + datetime.timedelta(days=30 * i), amount=amount, label=label
        )
        for i in range(count)
    ]


def _d(y: int, m: int, d: int) -> datetime.date:
    return datetime.date(y, m, d)


# ---------------------------------------------------------------------------
# Series keep their debits
# ---------------------------------------------------------------------------


def test_a_series_keeps_its_debits() -> None:
    debits = _monthly("STREAMFLIX", 1399, 4, _d(2025, 1, 5))
    [series] = detect_series(debits)
    assert [(h.date, h.amount) for h in series.hits] == [
        (d.date, d.amount) for d in debits
    ]


# ---------------------------------------------------------------------------
# chain_series
# ---------------------------------------------------------------------------


def test_successive_prices_of_one_label_form_one_chain() -> None:
    debits = (
        _monthly("STREAM", 1199, 4, _d(2024, 1, 5))
        + _monthly("STREAM", 1399, 4, _d(2024, 5, 4))
        + _monthly("STREAM", 1599, 4, _d(2024, 9, 1))
    )
    [chain] = chain_series(detect_series(debits))
    assert chain.key == "STREAM"
    assert [s.amount for s in chain.series] == [1199, 1399, 1599]
    assert chain.amount == 1599
    assert chain.first_date == _d(2024, 1, 5)
    assert len(chain.hits) == 12


def test_two_formulas_billed_side_by_side_stay_two_chains() -> None:
    debits = _monthly("APPSTORE", 99, 6, _d(2025, 1, 3)) + _monthly(
        "APPSTORE", 2595, 6, _d(2025, 1, 10)
    )
    chains = chain_series(detect_series(debits))
    assert sorted(c.amount for c in chains) == [99, 2595]


def test_a_long_gap_starts_a_new_chain() -> None:
    debits = _monthly("GYM", 2990, 4, _d(2024, 1, 5)) + _monthly(
        "GYM", 3290, 4, _d(2025, 1, 5)
    )
    assert len(chain_series(detect_series(debits))) == 2


# ---------------------------------------------------------------------------
# price_segments
# ---------------------------------------------------------------------------


def test_price_segments_follow_the_amount() -> None:
    hits = [
        (_d(2025, 1, 5), 999),
        (_d(2025, 2, 5), 999),
        (_d(2025, 3, 5), 1010),  # within tolerance: same segment
        (_d(2025, 4, 5), 1299),
        (_d(2025, 5, 5), 1299),
    ]
    segments = price_segments(hits)
    assert [(s.start, s.end, s.amount, s.count) for s in segments] == [
        (_d(2025, 1, 5), _d(2025, 3, 5), 999, 3),
        (_d(2025, 4, 5), _d(2025, 5, 5), 1299, 2),
    ]


def test_no_hits_no_segments() -> None:
    assert price_segments([]) == []


# ---------------------------------------------------------------------------
# is_running
# ---------------------------------------------------------------------------


def test_running_within_one_and_a_half_periods() -> None:
    assert is_running(_d(2026, 1, 1), Period.MONTHLY, _d(2026, 2, 10))
    assert not is_running(_d(2026, 1, 1), Period.MONTHLY, _d(2026, 2, 20))
    assert is_running(_d(2025, 6, 1), Period.YEARLY, _d(2026, 2, 1))


# ---------------------------------------------------------------------------
# suggest_links
# ---------------------------------------------------------------------------


def _span(
    line_id: str,
    key: str,
    first: datetime.date,
    last: datetime.date,
    first_amount: int,
    last_amount: int,
) -> LineSpan:
    return LineSpan(
        id=line_id,
        key=key,
        first_date=first,
        last_date=last,
        first_amount=first_amount,
        last_amount=last_amount,
        period=Period.MONTHLY,
    )


def test_successive_labels_at_the_exact_same_amount_are_suggested() -> None:
    spans = [
        _span("a", "EPOCH SWEA", _d(2024, 10, 14), _d(2025, 3, 11), 1918, 1918),
        _span("b", "EPOCH VRPA", _d(2025, 4, 10), _d(2025, 8, 8), 1918, 1918),
        _span("c", "EPOCH APIX", _d(2025, 9, 8), _d(2025, 11, 6), 1918, 1918),
    ]
    assert suggest_links(spans) == [("a", "b"), ("b", "c")]


def test_a_close_but_different_amount_is_never_suggested() -> None:
    spans = [
        _span("a", "FREE MOBILE", _d(2024, 2, 22), _d(2025, 7, 22), 1999, 1999),
        _span("b", "EPOCH APIX", _d(2025, 9, 8), _d(2025, 11, 6), 1918, 1918),
        _span("c", "ORANGE", _d(2024, 11, 12), _d(2025, 11, 7), 2999, 2999),
        _span("d", "BOUYGUES", _d(2025, 12, 15), _d(2026, 2, 12), 2399, 2399),
    ]
    assert suggest_links(spans) == []


def test_a_line_that_started_long_before_is_not_a_successor() -> None:
    spans = [
        _span("a", "ORANGE", _d(2024, 5, 6), _d(2025, 11, 3), 1599, 1599),
        _span("b", "STREAM", _d(2024, 2, 28), _d(2026, 1, 28), 1199, 1599),
    ]
    assert suggest_links(spans) == []


def test_too_long_a_gap_is_not_suggested() -> None:
    spans = [
        _span("a", "OLD", _d(2024, 1, 5), _d(2024, 6, 5), 999, 999),
        _span("b", "NEW", _d(2024, 12, 5), _d(2025, 6, 5), 999, 999),
    ]
    assert suggest_links(spans) == []
