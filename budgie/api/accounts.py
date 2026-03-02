"""Accounts CRUD router."""

from fastapi import APIRouter, HTTPException, status

from budgie.api.deps import CurrentUser, DBSession
from budgie.schemas.account import AccountCreate, AccountRead, AccountUpdate
from budgie.services.account import (
    create_account,
    delete_account,
    get_account,
    get_accounts,
    update_account,
)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    db: DBSession,
    current_user: CurrentUser,
) -> list[AccountRead]:
    """List all accounts for the authenticated user.

    Args:
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        List of account data.
    """
    accounts = await get_accounts(db, current_user.id)
    return [AccountRead.model_validate(a) for a in accounts]


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account_endpoint(
    schema: AccountCreate,
    db: DBSession,
    current_user: CurrentUser,
) -> AccountRead:
    """Create a new account for the authenticated user.

    Args:
        schema: Account creation data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Created account data.
    """
    account = await create_account(db, schema, current_user.id)
    return AccountRead.model_validate(account)


@router.get("/{account_id}", response_model=AccountRead)
async def get_account_endpoint(
    account_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> AccountRead:
    """Get a single account by ID.

    Args:
        account_id: Account primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Account data.

    Raises:
        HTTPException: 404 if account not found or not owned by user.
    """
    account = await get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    return AccountRead.model_validate(account)


@router.put("/{account_id}", response_model=AccountRead)
async def update_account_endpoint(
    account_id: int,
    schema: AccountUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> AccountRead:
    """Partially update an account.

    Args:
        account_id: Account primary key.
        schema: Partial update data.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        Updated account data.

    Raises:
        HTTPException: 404 if account not found.
    """
    account = await get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    updated = await update_account(db, account, schema)
    return AccountRead.model_validate(updated)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account_endpoint(
    account_id: int,
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Delete an account.

    Args:
        account_id: Account primary key.
        db: Async database session.
        current_user: JWT-authenticated user.

    Raises:
        HTTPException: 404 if account not found.
    """
    account = await get_account(db, account_id, current_user.id)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    await delete_account(db, account)
