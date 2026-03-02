"""Pydantic schemas for the categorization engine."""

from typing import Literal

from pydantic import BaseModel, Field


class CategorizeRequest(BaseModel):
    """A single transaction to categorize.

    Attributes:
        payee_name: The payee / merchant name extracted from the bank export.
        memo: Optional free-text memo or description for the transaction.
    """

    payee_name: str | None = None
    memo: str | None = None


class CategorizeResult(BaseModel):
    """Categorization result for a single transaction.

    Attributes:
        category_id: The matched category ID, or ``None`` if no match.
        confidence: How the category was determined.
            - ``"auto"``  — matched via the payee's ``auto_category_id``.
            - ``"rule"``  — matched by a ``CategoryRule``.
            - ``"none"``  — no match found.
    """

    category_id: int | None
    confidence: Literal["auto", "rule", "none"]


class BatchCategorizeRequest(BaseModel):
    """Batch categorization request.

    Attributes:
        transactions: List of transactions to categorize (at least one).
    """

    transactions: list[CategorizeRequest] = Field(..., min_length=1)


class BatchCategorizeResponse(BaseModel):
    """Batch categorization response.

    Attributes:
        results: One :class:`CategorizeResult` per input transaction,
            in the same order.
    """

    results: list[CategorizeResult]
