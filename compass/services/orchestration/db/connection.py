import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    global _pool
    dsn = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[asyncpg.Connection, None]:
    global _pool
    if _pool is None:
        await init_pool()
    async with _pool.acquire() as conn:
        yield conn
