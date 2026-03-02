"""Base types for bank file importers."""

from __future__ import annotations

import datetime
import hashlib
from abc import ABC, abstractmethod
from typing import IO

from pydantic import BaseModel, model_validator


class ImportedTransaction(BaseModel):
    """A transaction parsed from a bank export file.

    Attributes:
        date: Transaction date.
        amount: Amount in integer centimes (e.g., -5050 = -50.50€).
        description: Transaction label / memo.
        payee_name: Payee name, if available.
        reference: Bank reference (e.g., FITID for OFX files).
        import_hash: SHA-256 hash used for deduplication.
            Auto-computed from canonical fields when not provided.
    """

    date: datetime.date
    amount: int
    description: str
    payee_name: str | None = None
    reference: str | None = None
    import_hash: str = ""

    @model_validator(mode="after")
    def compute_import_hash(self) -> ImportedTransaction:
        """Compute import_hash from canonical fields if not already set."""
        if not self.import_hash:
            canonical = (
                f"{self.date}|{self.amount}|{self.description}|{self.reference or ''}"
            )
            self.import_hash = hashlib.sha256(canonical.encode()).hexdigest()
        return self


class BaseImporter(ABC):
    """Abstract base class for all bank file importers."""

    @abstractmethod
    def parse(self, stream: IO[bytes], **kwargs: object) -> list[ImportedTransaction]:
        """Parse a bank export file and return a list of transactions.

        Args:
            stream: Binary file-like object to read from.
            **kwargs: Importer-specific parameters.

        Returns:
            List of parsed ImportedTransaction objects.
        """


def to_centimes(value: float | int | str) -> int:
    """Convert a raw monetary value to integer centimes.

    Handles floats, ints, and string representations (including French
    format with comma decimal separator and space thousands separator).

    Args:
        value: Raw amount value from a parsed file.

    Returns:
        Amount expressed in integer centimes.

    Examples:
        >>> to_centimes(-50.50)
        -5050
        >>> to_centimes("3 829,82")
        382982
    """
    if isinstance(value, int | float):
        return round(float(value) * 100)
    cleaned = str(value).strip().replace("\xa0", "").replace(" ", "")
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    return round(float(cleaned) * 100)
