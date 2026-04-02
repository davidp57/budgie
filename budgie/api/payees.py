"""Payees CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession, SessionKey
from budgie.schemas.payee import PayeeCreate, PayeeRead, PayeeUpdate
from budgie.services.payee import (
    create_payee,
    delete_payee,
    get_payee,
    get_payees,
    update_payee,
)

router = APIRouter(prefix="/api/payees", tags=["payees"])


@router.get("", response_model=list[PayeeRead])
async def list_payees(
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> list[PayeeRead]:
    """List all payees for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        List of payee data.
    """
    payees = await get_payees(db, current_user.id, session_key=session_key)
    return [PayeeRead.model_validate(p) for p in payees]


@router.post("", response_model=PayeeRead, status_code=status.HTTP_201_CREATED)
async def create_payee_endpoint(
    schema: PayeeCreate,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> PayeeRead:
    """Create a new payee.

    Args:
        schema: Payee creation data.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption.

    Returns:
        Created payee data.
    """
    payee = await create_payee(db, schema, current_user.id, session_key=session_key)
    return PayeeRead.model_validate(payee)


@router.get("/{payee_id}", response_model=PayeeRead)
async def get_payee_endpoint(
    payee_id: int,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> PayeeRead:
    """Get a single payee by ID.

    Args:
        payee_id: Payee primary key.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for decryption.

    Returns:
        Payee data.

    Raises:
        HTTPException: 404 if payee not found.
    """
    payee = await get_payee(db, payee_id, current_user.id, session_key=session_key)
    if payee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payee not found"
        )
    return PayeeRead.model_validate(payee)


@router.put("/{payee_id}", response_model=PayeeRead)
async def update_payee_endpoint(
    payee_id: int,
    schema: PayeeUpdate,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> PayeeRead:
    """Partially update a payee.

    Args:
        payee_id: Payee primary key.
        schema: Partial update data.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key for encryption/decryption.

    Returns:
        Updated payee data.

    Raises:
        HTTPException: 404 if payee not found.
    """
    payee = await get_payee(db, payee_id, current_user.id, session_key=session_key)
    if payee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payee not found"
        )
    updated = await update_payee(db, payee, schema, session_key=session_key)
    return PayeeRead.model_validate(updated)


@router.delete("/{payee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payee_endpoint(
    payee_id: int,
    db: DBSession,
    current_user: CurrentUser,
    session_key: SessionKey,
) -> None:
    """Delete a payee.

    Args:
        payee_id: Payee primary key.
        db: Async database session.
        current_user: JWT-authenticated user.
        session_key: AES-256-GCM session key (used for get check only).

    Raises:
        HTTPException: 404 if payee not found.
    """
    payee = await get_payee(db, payee_id, current_user.id, session_key=session_key)
    if payee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payee not found"
        )
    await delete_payee(db, payee)
