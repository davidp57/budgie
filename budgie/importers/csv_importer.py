"""CSV bank file importer."""

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


class CsvImporter(BaseImporter):
    """Importer for CSV bank export files.

    Supports flexible column mapping, multiple date formats, custom
    separators, and French-style decimal notation.
    """

    def parse(  # type: ignore[override]
        self,
        stream: IO[bytes],
        column_map: dict[str, str],
        date_format: str = "%Y-%m-%d",
        separator: str = ",",
        decimal: str = ".",
        thousands: str = "",
        encoding: str = "utf-8",
    ) -> list[ImportedTransaction]:
        """Parse a CSV bank file.

        Args:
            stream: Binary stream containing the CSV data.
            column_map: Mapping from logical fields to CSV column names.
                Supported keys: ``date``, ``description``, ``amount``,
                ``debit``, ``credit``, ``payee``.
            date_format: :func:`datetime.datetime.strptime` format string
                for dates (default: ``"%Y-%m-%d"``).
            separator: Column delimiter (default: ``","``).
            decimal: Decimal separator for amounts (default: ``"."``;
                use ``","`` for French format).
            thousands: Thousands separator for amounts (default: ``""``).
            encoding: File encoding (default: ``"utf-8"``).

        Returns:
            List of parsed :class:`~budgie.importers.base.ImportedTransaction`
            objects, one per non-empty row.

        Raises:
            ValueError: If ``column_map`` lacks both ``amount`` and the
                ``debit``/``credit`` pair.
        """
        df: pd.DataFrame = pd.read_csv(
            stream,
            sep=separator,
            decimal=decimal,
            thousands=thousands if thousands else None,
            encoding=encoding,
            skip_blank_lines=True,
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


def _parse_date(value: object, date_format: str) -> datetime.date:
    """Parse a raw date value into a :class:`datetime.date`.

    Args:
        value: Raw value from a DataFrame cell.
        date_format: strptime format string used for string values.

    Returns:
        Parsed date.
    """
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return datetime.datetime.strptime(str(value).strip(), date_format).date()
