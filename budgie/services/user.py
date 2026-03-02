"""User service: database operations for the User model."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from budgie.models.user import User
from budgie.schemas.user import UserCreate
from budgie.services.auth import hash_password


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Fetch a user by username.

    Args:
        db: Async database session.
        username: Username to look up.

    Returns:
        User instance if found, None otherwise.
    """
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, schema: UserCreate) -> User:
    """Create a new user with a hashed password.

    Args:
        db: Async database session.
        schema: Validated user creation schema.

    Returns:
        Newly created User instance.
    """
    user = User(
        username=schema.username,
        hashed_password=hash_password(schema.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
