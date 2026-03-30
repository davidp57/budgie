"""Shared test fixtures for Budgie backend tests.

Provides an async test database, a test client, and helper fixtures
for all backend tests.
"""

from collections.abc import AsyncGenerator

import budgie.models  # noqa: F401 — registers all models with Base.metadata
import pytest_asyncio
from budgie.database import Base, get_db
from budgie.limiter import limiter
from budgie.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test.

    Creates all tables before the test and drops them after.

    Yields:
        AsyncSession: A test database session.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP test client with overridden DB dependency.

    Args:
        db_session: The test database session fixture.

    Yields:
        AsyncClient: An httpx async client bound to the test app.
    """

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an authenticated HTTP test client (user 'alice').

    Registers a user 'alice', logs in, and returns a client with the
    Authorization Bearer header pre-set.

    Args:
        client: The base test client fixture.

    Yields:
        AsyncClient: An httpx async client with JWT auth header.
    """
    await client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "AlicePassword1"},
    )
    login = await client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "AlicePassword1"},
    )
    token = login.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    # Clean up auth header
    del client.headers["Authorization"]


@pytest_asyncio.fixture(autouse=True)
async def _disable_rate_limiting() -> AsyncGenerator[None, None]:
    """Disable the SlowAPI rate limiter for every test.

    All test requests originate from 127.0.0.1 and would otherwise
    trigger the 5/minute login limit across the test suite.

    Yields:
        None
    """
    limiter.enabled = False  # type: ignore[attr-defined]
    yield
    limiter.enabled = True  # type: ignore[attr-defined]
