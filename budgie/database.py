"""Async SQLAlchemy engine and session factory.

Provides the database engine, session maker, and base model class
for all ORM models.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from budgie.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session.

    FastAPI dependency that provides a database session per request
    and ensures it is closed after the request is complete.

    Yields:
        AsyncSession: An async SQLAlchemy session.
    """
    async with async_session_factory() as session:
        yield session
