"""Excel bank file importer."""

from __future__ import annotations

import datetime
from typing import IO

import pandas as pd

from budgie.importers.base import BaseImporter, ImportedTransaction, to_centimes

# Logical field name constants used as column_map keys
_DATE = "date"
_DESCRIPTION = "description"
_AMOUNT = "amount"
_DEBIT = "debit"
_CREDIT = "credit"
_PAYEE = "payee"


class ExcelImporter(BaseImporter):
    """Importer for Excel (.xlsx / .xls) bank export files.

    Uses :mod:`pandas` with :mod:`openpyxl` as the engine.
    Supports files with or without a header row via the ``header``
    parameter, and flexible column mapping by name or integer index.
    """

    def parse(  # type: ignore[override]
        self,
        stream: IO[bytes],
        column_map: dict[str, str | int],
        date_format: str | None = None,
        header: int | None = 0,
    ) -> list[ImportedTransaction]:
        """Parse an Excel bank file.

        Args:
            stream: Binary stream containing the Excel file.
            column_map: Mapping from logical fields to column names or
                zero-based integer indices.  Supported keys: ``date``,
                ``description``, ``amount``, ``debit``, ``credit``,
                ``payee``.
            date_format: :func:`datetime.datetime.strptime` format string
                for string date cells.  When ``None``, pandas-native date
                objects are used directly (no string parsing).
            header: Row index of the header row (default: ``0``).
                Pass ``None`` for files without a header row; column
                positions will then be integer indices.

        Returns:
            List of parsed :class:`~budgie.importers.base.ImportedTransaction`
            objects.

        Raises:
            ValueError: If ``column_map`` lacks both ``amount`` and the
                ``debit``/``credit`` pair.
        """
        df: pd.DataFrame = pd.read_excel(
            stream,
            header=header,
        )
        df = df.dropna(how="all")

        transactions: list[ImportedTransaction] = []

        for _, row in df.iterrows():
            date_raw = row[column_map[_DATE]]
            if pd.isna(date_raw):
                continue
            txn_date = _parse_date(date_raw, date_format)

            if _AMOUNT in column_map:
                amount_centimes = to_centimes(row[column_map[_AMOUNT]])
            elif _DEBIT in column_map and _CREDIT in column_map:
                debit_raw = row[column_map[_DEBIT]]
                credit_raw = row[column_map[_CREDIT]]
                debit = to_centimes(debit_raw) if not pd.isna(debit_raw) else 0
                credit = to_centimes(credit_raw) if not pd.isna(credit_raw) else 0
                amount_centimes = credit - debit
            else:
                raise ValueError(
                    "column_map must include 'amount' or both 'debit' and 'credit'"
                )

            description = str(row[column_map[_DESCRIPTION]]).strip()

            payee_name: str | None = None
            if _PAYEE in column_map:
                raw_payee = row[column_map[_PAYEE]]
                if not pd.isna(raw_payee):
                    payee_name = str(raw_payee).strip() or None

            transactions.append(
                ImportedTransaction(
                    date=txn_date,
                    amount=amount_centimes,
                    description=description,
                    payee_name=payee_name,
                )
            )

        return transactions


def _parse_date(value: object, date_format: str | None) -> datetime.date:
    """Parse a raw cell value into a :class:`datetime.date`.

    Args:
        value: Raw value from a DataFrame cell (datetime, date or string).
        date_format: strptime format string, or ``None`` to auto-detect
            ISO-8601 (``YYYY-MM-DD``) strings and native date/datetime types.

    Returns:
        Parsed date.

    Raises:
        ValueError: If the value is a non-ISO string and no ``date_format``
            was provided.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if date_format is None:
        # Try ISO-8601 auto-detection (YYYY-MM-DD) before giving up
        try:
            return datetime.date.fromisoformat(str(value).strip())
        except ValueError:
            raise ValueError(
                f"Cannot parse date '{value!r}' without a date_format string. "
                "Provide a strptime format string if the date is not ISO-8601."
            ) from None
    return datetime.datetime.strptime(str(value).strip(), date_format).date()
