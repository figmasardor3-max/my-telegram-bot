import logging
from typing import Optional, Union
import asyncpg
from app.database.sqlite_adapter import SQLitePool

logger = logging.getLogger(__name__)

_pool: Optional[Union[asyncpg.Pool, SQLitePool]] = None
_is_sqlite: bool = False


def is_sqlite() -> bool:
    return _is_sqlite


async def init_pool(dsn: str, min_size: int = 2, max_size: int = 15) -> Union[asyncpg.Pool, SQLitePool]:
    """Initialize the global database pool (asyncpg for PostgreSQL, SQLitePool as local fallback)."""
    global _pool, _is_sqlite
    if _pool is not None:
        return _pool

    if dsn.startswith("sqlite"):
        db_path = dsn.replace("sqlite:///", "").replace("sqlite://", "") or "levelup.db"
        logger.info(f"Using SQLite database: {db_path}")
        _pool = SQLitePool(db_path)
        _is_sqlite = True
        return _pool

    logger.info("Initializing asyncpg connection pool for PostgreSQL...")
    try:
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=min_size,
            max_size=max_size,
            command_timeout=60,
            timeout=5.0
        )
        _is_sqlite = False
        logger.info("PostgreSQL database connection pool established.")
        return _pool
    except Exception as e:
        logger.warning(
            f"Could not connect to PostgreSQL at {dsn}: {e}.\n"
            f"🔄 Falling back to local SQLite database (levelup.db) for local execution."
        )
        _pool = SQLitePool("levelup.db")
        _is_sqlite = True
        return _pool


async def get_pool() -> Union[asyncpg.Pool, SQLitePool]:
    """Get the active database pool."""
    if _pool is None:
        raise RuntimeError("Database pool has not been initialized.")
    return _pool


async def close_pool() -> None:
    """Close the global database pool."""
    global _pool
    if _pool is not None:
        logger.info("Closing database pool...")
        await _pool.close()
        _pool = None
        logger.info("Database pool closed.")
