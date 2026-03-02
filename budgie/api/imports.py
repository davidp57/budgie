"""Import API router — parse and confirm bank file imports."""

from __future__ import annotations

import io

from fastapi import APIRouter, HTTPException, UploadFile, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.importers.base import ImportedTransaction
from budgie.importers.csv_importer import CsvImporter
from budgie.importers.excel_importer import ExcelImporter
from budgie.importers.ofx_importer import OfxImporter
from budgie.importers.qif_importer import QifImporter
from budgie.schemas.importer import (
    ConfirmImportRequest,
    ImportedTransactionSchema,
    ImportPreviewResponse,
    ImportResultResponse,
)
from budgie.services.importer import ImportResult, confirm_import

router = APIRouter(prefix="/api/imports", tags=["imports"])

# Supported file-format identifiers
_SUPPORTED_FORMATS = {"csv", "excel", "qif", "ofx"}


@router.post("/parse", response_model=ImportPreviewResponse)
async def parse_import(
    file: UploadFile,
    file_format: str,
    _current_user: CurrentUser,
) -> ImportPreviewResponse:
    """Parse an uploaded bank export file and return a preview.

    The transactions are **not** persisted — call ``/confirm`` after
    reviewing the preview.

    Args:
        file: The bank export file to parse.
        file_format: One of ``csv``, ``excel``, ``qif``, ``ofx``.
        _current_user: JWT-authenticated user (authorisation guard).

    Returns:
        Preview list of parsed transactions.

    Raises:
        HTTPException: 400 if the format is unsupported or the file
            cannot be parsed.
    """
    fmt = file_format.lower()
    if fmt not in _SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{file_format}'. "
            f"Supported: {sorted(_SUPPORTED_FORMATS)}",
        )

    content = await file.read()
    import io

    stream = io.BytesIO(content)

    try:
        transactions = _parse_stream(stream, fmt)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {exc}",
        ) from exc

    schemas = [_to_schema(t) for t in transactions]
    return ImportPreviewResponse(transactions=schemas, total=len(schemas))


@router.post(
    "/confirm",
    response_model=ImportResultResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_import_endpoint(
    body: ConfirmImportRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> ImportResultResponse:
    """Persist previously-parsed transactions into the database.

    Duplicate transactions (matching ``import_hash``) are silently
    skipped and counted in the ``duplicates`` field of the response.

    Args:
        body: Account ID and list of transactions to import.
        db: Async database session.
        current_user: JWT-authenticated user (ownership check).

    Returns:
        Counts of imported and duplicate transactions.
    """
    # Convert schema objects back to domain model
    domain_txns = [
        ImportedTransaction(
            date=t.date,
            amount=t.amount,
            description=t.description,
            payee_name=t.payee_name,
            reference=t.reference,
            import_hash=t.import_hash,
        )
        for t in body.transactions
    ]

    result: ImportResult = await confirm_import(db, body.account_id, domain_txns)
    return ImportResultResponse(imported=result.imported, duplicates=result.duplicates)


def _parse_stream(
    stream: io.BytesIO,
    fmt: str,
) -> list[ImportedTransaction]:
    """Dispatch parsing to the appropriate importer.

    Args:
        stream: In-memory binary stream of the uploaded file.
        fmt: Lowercase format identifier.

    Returns:
        List of parsed transactions with default column mapping.

    Raises:
        ValueError: If the format string is not recognised.
    """
    if fmt == "csv":
        _map = {"date": "date", "description": "description", "amount": "amount"}
        return CsvImporter().parse(stream, column_map=_map)
    if fmt == "excel":
        _emap: dict[str, str | int] = {
            "date": "date",
            "description": "description",
            "amount": "amount",
        }
        return ExcelImporter().parse(stream, column_map=_emap)
    if fmt == "qif":
        return QifImporter().parse(stream)
    if fmt == "ofx":
        return OfxImporter().parse(stream)
    raise ValueError(f"Unknown format: {fmt!r}")


def _to_schema(txn: ImportedTransaction) -> ImportedTransactionSchema:
    """Convert a domain :class:`ImportedTransaction` to a schema object.

    Args:
        txn: Domain transaction object.

    Returns:
        Schema object ready for serialisation.
    """
    return ImportedTransactionSchema(
        date=txn.date,
        amount=txn.amount,
        description=txn.description,
        payee_name=txn.payee_name,
        reference=txn.reference,
        import_hash=txn.import_hash,
    )
