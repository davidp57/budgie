"""Transactions CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.transaction import (
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)
from budgie.services.transaction import (
    create_transaction,
    delete_transaction,
    get_transaction,
    get_transactions,
    update_transaction,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
async def list_transactions(
    db: DBSession,
    current_user: CurrentUser,
    account_id: int | None = None,
) -> list[TransactionRead]:
    """List transactions for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.
        account_id: Optional account filter.

    Returns:
        List of transaction data.
    """
    txns = await get_transactions(db, current_user.id, account_id)
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
