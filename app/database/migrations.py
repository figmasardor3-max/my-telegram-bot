import logging
from pathlib import Path
from typing import Union
import asyncpg
from app.database.sqlite_adapter import SQLitePool
from app.database.connection import is_sqlite

logger = logging.getLogger(__name__)


async def apply_migrations(pool: Union[asyncpg.Pool, SQLitePool]) -> None:
    """
    Applies .sql migration files in order.
    Uses schema_migrations tracking table to guarantee each migration runs only once.
    """
    migrations_dir = Path(__file__).resolve().parent.parent.parent / "migrations"
    use_sqlite = is_sqlite() or isinstance(pool, SQLitePool)

    async with pool.acquire() as conn:
        # Create schema_migrations tracking table
        if use_sqlite:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT UNIQUE NOT NULL,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
        else:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)

        applied_rows = await conn.fetch("SELECT version FROM schema_migrations;")
        applied = {row["version"] for row in applied_rows}

        if use_sqlite:
            # Use SQLite schema file
            sqlite_file = migrations_dir / "001_initial_schema_sqlite.sql"
            if sqlite_file.exists() and sqlite_file.name not in applied:
                logger.info(f"Applying SQLite migration: {sqlite_file.name}")
                sql = sqlite_file.read_text(encoding="utf-8")
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1);",
                    sqlite_file.name
                )
                logger.info(f"Migration {sqlite_file.name} applied successfully.")
        else:
            # PostgreSQL migrations
            migration_files = sorted(migrations_dir.glob("*.sql"))
            for file in migration_files:
                if "_sqlite" in file.name:
                    continue
                version = file.name
                if version in applied:
                    continue

                logger.info(f"Applying PostgreSQL migration: {version}")
                sql_content = file.read_text(encoding="utf-8")
                async with conn.transaction():
                    await conn.execute(sql_content)
                    await conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES ($1);",
                        version
                    )
                logger.info(f"Migration {version} applied successfully.")
