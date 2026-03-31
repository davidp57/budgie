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

    Returns None when the user has not set up encryption or when the key is
    not in the in-memory store (e.g. after a server restart — the user must
    re-unlock).

    Args:
        current_user: Authenticated user from JWT.

    Returns:
        32-byte key or None.
    """
    if not current_user.is_encrypted:
        return None
    return key_store.get(current_user.id)


CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
SessionKey = Annotated[bytes | None, Depends(get_session_key)]
