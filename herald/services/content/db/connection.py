import asyncpg
import os
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL", "postgresql://localhost/pcop")
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)
        logger.info("HERALD: asyncpg pool created")
    return _pool


@asynccontextmanager
async def get_db_session():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
