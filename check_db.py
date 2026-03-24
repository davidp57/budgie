"""Temporary DB diagnostic script."""

import asyncio
from sqlalchemy import text
from budgie.database import engine


async def check() -> None:
    async with engine.begin() as conn:
        r = await conn.execute(text("SELECT version_num FROM alembic_version"))
        print("Alembic version:", r.scalar())
        r2 = await conn.execute(text("PRAGMA table_info(users)"))
        cols = [row[1] for row in r2.fetchall()]
        print("Users cols:", cols)


asyncio.run(check())
