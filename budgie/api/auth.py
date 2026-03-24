"""Authentication router: register and login endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.api.deps import get_current_user
from budgie.database import get_db
from budgie.models.user import User
from budgie.schemas.auth import (
    EncryptionActionResponse,
    LoginRequest,
    SetupEncryptionRequest,
    TokenResponse,
)
from budgie.schemas.user import UserCreate, UserRead
from budgie.services.auth import create_access_token, verify_password
from budgie.services.encryption import setup_user_encryption, verify_user_passphrase
from budgie.services.key_store import key_store
from budgie.services.user import create_user, get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])
DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    schema: UserCreate,
    db: DB,
) -> UserRead:
    """Register a new user account.

    Args:
        schema: User creation data (username + password).
        db: Async database session.

    Returns:
        Created user data (no password).

    Raises:
        HTTPException: 409 if username already exists.
    """
    existing = await get_user_by_username(db, schema.username)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered",
        )
    user = await create_user(db, schema)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: LoginRequest,
    db: DB,
) -> TokenResponse:
    """Authenticate a user and return a JWT access token.

    Args:
        credentials: Login credentials (username + password).
        db: Async database session.

    Returns:
        JWT access token.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = await get_user_by_username(db, credentials.username)
    if user is None or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        needs_encryption_setup=not user.is_encrypted,
        is_encrypted=user.is_encrypted,
    )


@router.post("/setup-encryption", response_model=EncryptionActionResponse)
async def setup_encryption(
    schema: SetupEncryptionRequest,
    db: DB,
    current_user: CurrentUser,
) -> EncryptionActionResponse:
    """Set up encryption for the authenticated user (first time only).

    Args:
        schema: Passphrase used to derive the AES-256-GCM key.
        db: Async database session.
        current_user: Authenticated user from JWT.

    Returns:
        ``{"ok": true}`` on success.

    Raises:
        HTTPException: 409 if encryption is already set up.
    """
    if current_user.is_encrypted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Encryption already set up for this account.",
        )
    key = await setup_user_encryption(db, current_user, schema.passphrase)
    key_store.set(current_user.id, key)
    return EncryptionActionResponse()


@router.post("/unlock", response_model=EncryptionActionResponse)
async def unlock(
    schema: SetupEncryptionRequest,
    current_user: CurrentUser,
) -> EncryptionActionResponse:
    """Verify the passphrase for an already-encrypted account.

    Args:
        schema: Passphrase to verify.
        current_user: Authenticated user from JWT.

    Returns:
        ``{"ok": true}`` on success.

    Raises:
        HTTPException: 400 if encryption is not set up.
        HTTPException: 401 if the passphrase is incorrect.
    """
    if not current_user.is_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Encryption is not set up for this account.",
        )
    session_key = await verify_user_passphrase(current_user, schema.passphrase)
    if session_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect passphrase.",
        )
    key_store.set(current_user.id, session_key)
    return EncryptionActionResponse()


@router.post("/logout", response_model=EncryptionActionResponse)
async def logout(
    current_user: CurrentUser,
) -> EncryptionActionResponse:
    """Purge the session encryption key from server RAM.

    Args:
        current_user: Authenticated user from JWT.

    Returns:
        ``{"ok": true}``.
    """
    key_store.delete(current_user.id)
    return EncryptionActionResponse()
