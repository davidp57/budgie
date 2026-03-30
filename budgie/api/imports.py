"""Import API router — parse and confirm bank file imports."""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.config import settings
from budgie.importers.base import ImportedTransaction
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
    _current_user: CurrentUser,
    file_format: str = Query(..., description="One of: csv, excel, qif, ofx"),
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

    max_mb = settings.max_upload_size_bytes // (1024 * 1024)
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File too large (max {max_mb} MB).",
        )

    stream = io.BytesIO(content)

    try:
        transactions = _parse_stream(stream, fmt)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to parse file.",
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
            virtual_linked_id=t.virtual_linked_id,
        )
        for t in body.transactions
    ]

    try:
        result: ImportResult = await confirm_import(
            db, body.account_id, current_user.id, domain_txns
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    return ImportResultResponse(imported=result.imported, duplicates=result.duplicates)


def _parse_stream(
    stream: io.BytesIO,
    fmt: str,
) -> list[ImportedTransaction]:
    """Dispatch parsing to the appropriate importer.

    For CSV and Excel, column names and separators are auto-detected from
    the file headers to support exports from various banks (Boursorama,
    LCL, BNP, …).

    Args:
        stream: In-memory binary stream of the uploaded file.
        fmt: Lowercase format identifier.

    Returns:
        List of parsed transactions with auto-detected column mapping.

    Raises:
        ValueError: If the format string is not recognised or required
            columns cannot be found in the file.
    """
    if fmt == "csv":
        return _parse_csv_auto(stream)
    if fmt == "excel":
        return _parse_excel_auto(stream)
    if fmt == "qif":
        return QifImporter().parse(stream)
    if fmt == "ofx":
        return OfxImporter().parse(stream)
    raise ValueError(f"Unknown format: {fmt!r}")


# ---------------------------------------------------------------------------
# Column-name candidates for auto-detection
# ---------------------------------------------------------------------------
_DATE_CANDIDATES = ["dateop", "date", "date_operation", "dateoperation", "date op"]
_DESC_CANDIDATES = [
    "label",
    "libelle",
    "libellé",
    "description",
    "memo",
    "intitule",
    "intitulé",
    "detail",
    "détail",
    "wording",
]
_AMOUNT_CANDIDATES = ["amount", "montant", "valeur", "value"]
_DEBIT_CANDIDATES = ["debit", "débit", "montant debit", "montant débit"]
_CREDIT_CANDIDATES = ["credit", "crédit", "montant credit", "montant crédit"]
_PAYEE_CANDIDATES = ["supplierfound", "payee", "tiers", "beneficiaire", "bénéficiaire"]


def _detect_column(columns_lower: list[str], candidates: list[str]) -> str | None:
    """Return the first column (lowercased) that matches any candidate.

    Args:
        columns_lower: Lowercased column names from the dataframe.
        candidates: Ordered list of candidate names to try.

    Returns:
        Matched lowercased column name, or ``None``.
    """
    return next((cand for cand in candidates if cand in columns_lower), None)


def _parse_csv_auto(stream: io.BytesIO) -> list[ImportedTransaction]:
    """Parse a CSV file with automatic separator, decimal and column detection.

    Args:
        stream: Binary stream for the CSV file.

    Returns:
        List of parsed transactions.

    Raises:
        ValueError: If required columns cannot be found.
    """
    raw = stream.read()

    # Auto-detect separator: count `;` vs `,` on first non-empty line
    first_line = raw.split(b"\n")[0].decode("utf-8", errors="replace")
    separator = ";" if first_line.count(";") >= first_line.count(",") else ","

    # Auto-detect decimal separator: if separator is `;`, French files use `,`
    decimal = "," if separator == ";" else "."

    df: pd.DataFrame = pd.read_csv(
        io.BytesIO(raw),
        sep=separator,
        decimal=decimal,
        encoding="utf-8",
        skip_blank_lines=True,
    )
    df = df.dropna(how="all")

    return _dataframe_to_transactions(df)


def _parse_excel_auto(stream: io.BytesIO) -> list[ImportedTransaction]:
    """Parse an Excel file with automatic column detection.

    Handles both files with named headers and headerless exports (e.g.
    Boursorama) where the first row is immediately data.  When no header
    row is detected the function falls back to positional mapping based on
    the most common bank export layout:
    col 0 = date, col 2 = description, col 5 = payee, col 6 = amount.

    Args:
        stream: Binary stream for the Excel file.

    Returns:
        List of parsed transactions.

    Raises:
        ValueError: If required columns cannot be found.
    """
    df_with_header: pd.DataFrame = pd.read_excel(stream, header=0)
    df_with_header = df_with_header.dropna(how="all")

    # Check whether header detection succeeded by looking for known column names
    col_lower_with = [
        c.lower().strip() for c in df_with_header.columns if isinstance(c, str)
    ]
    has_date_col = _detect_column(col_lower_with, _DATE_CANDIDATES) is not None

    if has_date_col:
        return _dataframe_to_transactions(df_with_header)

    # No recognisable headers — re-read without header row
    stream.seek(0)
    df_no_header: pd.DataFrame = pd.read_excel(stream, header=None)
    df_no_header = df_no_header.dropna(how="all")

    # Assign logical names based on the most common bank export column order
    # (Boursorama / standard): 0=date, 2=label, 5=payee, 6=amount
    n_cols = len(df_no_header.columns)
    rename: dict[int, str] = {}
    if n_cols > 0:
        rename[0] = "date"
    if n_cols > 2:
        rename[2] = "label"
    if n_cols > 5:
        rename[5] = "supplierfound"
    if n_cols > 6:
        rename[6] = "amount"

    df_no_header = df_no_header.rename(columns=rename)
    return _dataframe_to_transactions(df_no_header)


def _dataframe_to_transactions(df: pd.DataFrame) -> list[ImportedTransaction]:
    """Convert a DataFrame to a list of ImportedTransaction using auto-detected columns.

    Args:
        df: DataFrame loaded from a bank export file.

    Returns:
        List of parsed transactions.

    Raises:
        ValueError: If a required column (date or description+amount) cannot
            be found.
    """
    # Build a lowercase→original mapping for case-insensitive matching
    # Skip columns with non-string names (e.g. NaN placeholders from Excel)
    col_lower_to_orig: dict[str, str] = {
        c.lower().strip(): c for c in df.columns if isinstance(c, str)
    }
    cols_lower = list(col_lower_to_orig.keys())

    date_col_lower = _detect_column(cols_lower, _DATE_CANDIDATES)
    desc_col_lower = _detect_column(cols_lower, _DESC_CANDIDATES)
    amount_col_lower = _detect_column(cols_lower, _AMOUNT_CANDIDATES)
    debit_col_lower = _detect_column(cols_lower, _DEBIT_CANDIDATES)
    credit_col_lower = _detect_column(cols_lower, _CREDIT_CANDIDATES)
    payee_col_lower = _detect_column(cols_lower, _PAYEE_CANDIDATES)

    if date_col_lower is None:
        raise ValueError(
            f"Could not find a date column. Found columns: {list(df.columns)}. "
            f"Expected one of: {_DATE_CANDIDATES}"
        )
    if desc_col_lower is None:
        raise ValueError(
            f"Could not find a description column. Found columns: {list(df.columns)}. "
            f"Expected one of: {_DESC_CANDIDATES}"
        )
    if amount_col_lower is None and not (debit_col_lower and credit_col_lower):
        raise ValueError(
            f"Could not find an amount column. Found columns: {list(df.columns)}. "
            f"Expected one of: {_AMOUNT_CANDIDATES} or debit+credit pair."
        )

    date_col = col_lower_to_orig[date_col_lower]
    desc_col = col_lower_to_orig[desc_col_lower]

    transactions: list[ImportedTransaction] = []

    for _, row in df.iterrows():
        date_raw = row[date_col]
        if pd.isna(date_raw):
            continue

        # Parse date — pd.to_datetime handles Timestamps, ISO strings, d/m/y…
        try:
            txn_date = pd.to_datetime(date_raw, dayfirst=False).date()
        except Exception:
            continue  # skip unparseable dates

        # Parse amount
        from budgie.importers.base import to_centimes

        if amount_col_lower is not None:
            amount_centimes = to_centimes(row[col_lower_to_orig[amount_col_lower]])
        else:
            assert debit_col_lower is not None and credit_col_lower is not None
            raw_debit = row[col_lower_to_orig[debit_col_lower]]
            raw_credit = row[col_lower_to_orig[credit_col_lower]]
            debit = 0 if pd.isna(raw_debit) else to_centimes(raw_debit)
            credit = 0 if pd.isna(raw_credit) else to_centimes(raw_credit)
            amount_centimes = credit - debit

        description = str(row[desc_col]).strip()

        payee_name: str | None = None
        if payee_col_lower is not None:
            raw_payee = row[col_lower_to_orig[payee_col_lower]]
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
