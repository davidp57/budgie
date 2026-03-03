"""User preferences router."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.api.deps import get_current_user
from budgie.database import get_db
from budgie.models.user import User
from budgie.schemas.user import UserPreferences, UserPreferencesUpdate

router = APIRouter(prefix="/api/users", tags=["users"])

DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/me/preferences", response_model=UserPreferences)
async def get_preferences(current_user: CurrentUser) -> User:
    """Return the preferences for the authenticated user.

    Args:
        current_user: JWT-authenticated user.

    Returns:
        UserPreferences with current settings.
    """
    return current_user


@router.put("/me/preferences", response_model=UserPreferences)
async def update_preferences(
    payload: UserPreferencesUpdate,
    db: DB,
    current_user: CurrentUser,
) -> User:
    """Update preferences for the authenticated user.

    Args:
        payload: New preference values.
        db: Async database session.
        current_user: JWT-authenticated user.

    Returns:
        UserPreferences with updated settings.
    """
    current_user.budget_mode = payload.budget_mode
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user
