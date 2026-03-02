"""Authentication router: register and login endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.database import get_db
from budgie.schemas.auth import LoginRequest, TokenResponse
from budgie.schemas.user import UserCreate, UserRead
from budgie.services.auth import create_access_token, verify_password
from budgie.services.user import create_user, get_user_by_username

router = APIRouter(prefix="/api/auth", tags=["auth"])
DB = Annotated[AsyncSession, Depends(get_db)]


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
    return TokenResponse(access_token=token)
