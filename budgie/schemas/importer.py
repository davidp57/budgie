"""Pydantic schemas for the import API."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field


class ImportedTransactionSchema(BaseModel):
    """A parsed transaction ready to be confirmed.

    Attributes:
        date: Transaction date.
        amount: Amount in integer centimes.
        description: Transaction label / memo.
        payee_name: Payee name, if available.
        reference: Bank reference, if available.
        import_hash: SHA-256 deduplication hash.
    """

    date: datetime.date
    amount: int
    description: str
    payee_name: str | None = None
    reference: str | None = None
    import_hash: str


class ImportPreviewResponse(BaseModel):
    """Response returned by ``POST /api/imports/parse``.

    Attributes:
        transactions: List of parsed transactions available for review.
        total: Total number of parsed transactions.
    """

    transactions: list[ImportedTransactionSchema]
    total: int


class ConfirmImportRequest(BaseModel):
    """Request body for ``POST /api/imports/confirm``.

    Attributes:
        account_id: Target account to import transactions into.
        transactions: Validated transactions to persist.
    """

    account_id: int
    transactions: list[ImportedTransactionSchema] = Field(min_length=1)


class ImportResultResponse(BaseModel):
    """Response returned by ``POST /api/imports/confirm``.

    Attributes:
        imported: Number of new transactions written.
        duplicates: Number of duplicates skipped.
    """

    imported: int
    duplicates: int
