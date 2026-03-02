"""FastAPI dependency injection helpers."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.database import get_db
from budgie.models.user import User
from budgie.services.auth import decode_token
from budgie.services.user import get_user_by_username

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Validate JWT token and return the current authenticated user.

    Args:
        credentials: Bearer token credentials from Authorization header.
        db: Async database session.

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


CurrentUser = Annotated[User, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
