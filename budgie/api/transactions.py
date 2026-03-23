"""Transactions CRUD router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    PlannedMatchRequest,
)
from budgie.services.transaction import (
    create_transaction,
    delete_transaction,
    get_transaction,
    get_transactions,
    get_planned_unlinked,
    link_planned,
    update_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/planned/unlinked", response_model=list[TransactionRead])
async def list_planned_unlinked(
    db: DBSession,
    current_user: CurrentUser,
) -> list[TransactionRead]:
    """List all unlinked (pending) planned transactions for the user.

    Returns planned transactions that have not yet been matched to a
    real imported transaction.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of pending planned transaction data.
    """
    txns = await get_planned_unlinked(db, current_user.id)
    return [TransactionRead.model_validate(t) for t in txns]


@router.post("/planned/match", response_model=TransactionRead)
async def match_planned_transaction(
    schema: PlannedMatchRequest,
    db: DBSession,
    current_user: CurrentUser,
) -> TransactionRead:
    """Link a real transaction to a planned one, marking the planned as reconciled.

    Args:
        schema: Match request with real and planned transaction IDs.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Updated real transaction data.

    Raises:
        HTTPException: 404 if either transaction is not found.
        HTTPException: 400 if the planned transaction ID is invalid.
    """
    real_txn = await get_transaction(db, schema.real_transaction_id, current_user.id)
    if real_txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Real transaction not found",
        )
    try:
        updated = await link_planned(
            db, real_txn, schema.planned_transaction_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return TransactionRead.model_validate(updated)


@router.get("", response_model=list[TransactionRead])
async def list_transactions(
    db: DBSession,
    current_user: CurrentUser,
    account_id: int | None = None,
    transaction_status: str | None = None,
    month: str | None = None,
    category_ids: Annotated[list[int] | None, Query()] = None,
) -> list[TransactionRead]:
    """List transactions for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.
        account_id: Optional account filter.
        transaction_status: Optional filter by status (planned/real/reconciled).
        month: Optional YYYY-MM month filter.
        category_ids: Optional list of category IDs to filter by (repeatable
            query param: ?category_ids=1&category_ids=2).

    Returns:
        List of transaction data.
    """
    cat_filter: list[int] | None = category_ids or None
    txns = await get_transactions(
        db, current_user.id, account_id, transaction_status, month, cat_filter
    )
    return [TransactionRead.model_validate(t) for t in txns]


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction_endpoint(
    schema: TransactionCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> TransactionRead:
    """Create a new transaction.

    Args:
        schema: Transaction creation data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Created transaction data.
    """
    txn = await create_transaction(db, schema)
    return TransactionRead.model_validate(txn)


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction_endpoint(
    transaction_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> TransactionRead:
    """Get a single transaction by ID.

    Args:
        transaction_id: Transaction primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Transaction data.

    Raises:
        HTTPException: 404 if not found.
    """
    txn = await get_transaction(db, transaction_id, current_user.id)
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return TransactionRead.model_validate(txn)


@router.put("/{transaction_id}", response_model=TransactionRead)
@router.patch("/{transaction_id}", response_model=TransactionRead)
async def update_transaction_endpoint(
    transaction_id: int,
    schema: TransactionUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> TransactionRead:
    """Partially update a transaction.

    Args:
        transaction_id: Transaction primary key.
        schema: Partial update data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Updated transaction data.

    Raises:
        HTTPException: 404 if not found.
    """
    txn = await get_transaction(db, transaction_id, current_user.id)
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    updated = await update_transaction(db, txn, schema)
    return TransactionRead.model_validate(updated)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction_endpoint(
    transaction_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete a transaction.

    Args:
        transaction_id: Transaction primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if not found.
    """
    txn = await get_transaction(db, transaction_id, current_user.id)
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    await delete_transaction(db, txn)
