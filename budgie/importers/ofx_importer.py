"""OFX / QFX bank file importer."""

from __future__ import annotations

import datetime
import hashlib
from decimal import Decimal
from typing import IO

from ofxtools import OFXTree  # type: ignore[attr-defined]

from budgie.importers.base import BaseImporter, ImportedTransaction


class OfxImporter(BaseImporter):
    """Importer for OFX / QFX bank export files.

    Supports both SGML (OFX 1.x) and XML (OFX 2.x) formats via
    :mod:`ofxtools`.  The bank-provided ``FITID`` is used as the stable
    transaction reference, and ``import_hash`` is computed as
    ``SHA-256(FITID)`` for reliable deduplication across re-imports.

    Uses ElementTree-based parsing (``findall``) to avoid strict OFX
    schema validation that would reject minimal or non-compliant files.
    """

    def parse(  # type: ignore[override]
        self,
        stream: IO[bytes],
    ) -> list[ImportedTransaction]:
        """Parse an OFX / QFX bank file.

        Args:
            stream: Binary stream containing the OFX data.

        Returns:
            List of parsed :class:`~budgie.importers.base.ImportedTransaction`
            objects.
        """
        tree = OFXTree()
        tree.parse(stream)

        transactions: list[ImportedTransaction] = []

        for elem in tree.findall(".//STMTTRN"):
            dtposted_str: str = elem.findtext("DTPOSTED") or ""
            trnamt_str: str = elem.findtext("TRNAMT") or "0"
            fitid: str = elem.findtext("FITID") or ""
            name: str = (elem.findtext("NAME") or "").strip()

            # OFX dates are YYYYMMDD[HHMMSS] — take first 8 chars
            txn_date = datetime.datetime.strptime(dtposted_str[:8], "%Y%m%d").date()

            amount_centimes = round(Decimal(trnamt_str) * 100)
            import_hash = hashlib.sha256(fitid.encode()).hexdigest()

            transactions.append(
                ImportedTransaction(
                    date=txn_date,
                    amount=amount_centimes,
                    description=name or fitid,
                    payee_name=name or None,
                    reference=fitid,
                    import_hash=import_hash,
                )
            )

        return transactions
