"""QIF bank file importer."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import IO

import quiffen

from budgie.importers.base import BaseImporter, ImportedTransaction


class QifImporter(BaseImporter):
    """Importer for QIF (Quicken Interchange Format) bank files.

    Uses the :mod:`quiffen` library for parsing.  Supports configurable
    date formats via the ``date_format`` parameter.
    """

    def parse(  # type: ignore[override]
        self,
        stream: IO[bytes],
        date_format: str = "%m/%d/%Y",
    ) -> list[ImportedTransaction]:
        """Parse a QIF bank file.

        Args:
            stream: Binary stream containing the QIF data.
            date_format: :func:`datetime.datetime.strptime` format for
                QIF date fields (default: ``"%m/%d/%Y"`` — US format).
                Use ``"%d/%m/%Y"`` for European day-first format.

        Returns:
            List of parsed :class:`~budgie.importers.base.ImportedTransaction`
            objects.
        """
        content = stream.read().decode("utf-8", errors="replace")
        day_first = date_format.startswith("%d")
        qif = quiffen.Qif.parse_string(content, day_first=day_first)

        transactions: list[ImportedTransaction] = []

        for account in qif.accounts.values():
            # account.transactions is {AccountType: [Transaction, ...]}
            for txn_list in account.transactions.values():
                for txn in txn_list:
                    txn_date = _ensure_date(txn.date)
                    if txn_date is None:
                        continue

                    raw_amount: Decimal = txn.amount or Decimal("0")
                    amount_centimes = round(float(raw_amount) * 100)

                    payee_name: str | None = (
                        str(txn.payee).strip() if txn.payee else None
                    )
                    description = (
                        str(txn.memo).strip() if txn.memo else (payee_name or "")
                    )

                    transactions.append(
                        ImportedTransaction(
                            date=txn_date,
                            amount=amount_centimes,
                            description=description,
                            payee_name=payee_name,
                        )
                    )

        return transactions


def _ensure_date(value: object) -> datetime.date | None:
    """Coerce a quiffen date value to :class:`datetime.date`.

    Args:
        value: The raw date value returned by the quiffen parser.

    Returns:
        A :class:`datetime.date`, or ``None`` if the value is absent.
    """
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return None
