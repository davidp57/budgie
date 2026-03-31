"""FastAPI dependency injection helpers."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.database import get_db
from budgie.models.user import User
from budgie.services.auth import decode_token
from budgie.services.key_store import key_store
from budgie.services.user import get_user_by_username

security = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(security)
    ] = None,
) -> User:
    """Validate JWT token and return the current authenticated user.

    Args:
        db: Async database session.
        credentials: Bearer token credentials from Authorization header.

    Returns:
        Authenticated User instance.

    Raises:
        HTTPException: 401 if the token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    try:
        payload = decode_token(credentials.credentials)
        username: object = payload.get("sub")
        if not isinstance(username, str):
            raise credentials_exception
    except JWTError as err:
        raise credentials_exception from err

    user = await get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


async def get_session_key(
    current_user: Annotated[User, Depends(get_current_user)],
) -> bytes | None:
    """Return the AES-256-GCM session key for the current user, or None.

    For non-encrypted accounts, returns None (encryption not configured).
    For encrypted accounts, returns the 32-byte key or raises HTTP 423 if
    the key is not present in the in-memory store (e.g. after a server
    restart — the user must call ``/unlock`` again).

    Args:
        current_user: Authenticated user from JWT.

    Returns:
        32-byte key for encrypted accounts, or None for non-encrypted accounts.

    Raises:
        HTTPException: 423 if the account is encrypted but the session key is
            not in RAM (user must re-unlock).
    """
    if not current_user.is_encrypted:
        return None
    key = key_store.get(current_user.id)
    if key is None:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                "Account encryption is locked. "
                "Please unlock before performing this operation."
            ),
        )
    return key


CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
SessionKey = Annotated[bytes | None, Depends(get_session_key)]
