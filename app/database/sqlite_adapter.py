import sqlite3
import re
import logging
from typing import Any, List, Optional
from datetime import datetime, date
import asyncpg

logger = logging.getLogger(__name__)


class SQLiteRecord(dict):
    """Dict-like record compatible with asyncpg.Record."""
    def __getitem__(self, key: str) -> Any:
        return super().__getitem__(key)

    def get(self, key: str, default: Any = None) -> Any:
        return super().get(key, default)


def _convert_row(cursor: sqlite3.Cursor, row: tuple) -> SQLiteRecord:
    d = {}
    for idx, col in enumerate(cursor.description):
        col_name = col[0]
        val = row[idx]
        # Parse ISO timestamps or dates into datetime/date objects if needed
        if isinstance(val, str) and ("-" in val and (":" in val or len(val) == 10)):
            try:
                if len(val) == 10:
                    d[col_name] = datetime.strptime(val, "%Y-%m-%d").date()
                else:
                    d[col_name] = datetime.fromisoformat(val)
            except Exception:
                d[col_name] = val
        else:
            d[col_name] = val
    return SQLiteRecord(d)


def _translate_query(sql: str) -> str:
    """Translates PostgreSQL specific syntax to SQLite compatible syntax."""
    # 1. Remove FOR UPDATE locks
    sql = re.sub(r'\s+FOR\s+UPDATE', '', sql, flags=re.IGNORECASE)

    # 2. Translate NOW() - make_interval(days => $1)
    sql = re.sub(
        r"NOW\(\)\s*-\s*make_interval\s*\(\s*days\s*=>\s*(\$\d+|\?)\s*\)",
        r"datetime('now', '-' || \1 || ' days')",
        sql,
        flags=re.IGNORECASE
    )

    # 3. Translate NOW() - INTERVAL 'N days'
    sql = re.sub(
        r"NOW\(\)\s*-\s*INTERVAL\s+'(\d+)\s+days'",
        r"datetime('now', '-\1 days')",
        sql,
        flags=re.IGNORECASE
    )

    # 4. Standalone INTERVAL or make_interval
    sql = re.sub(
        r"make_interval\s*\(\s*days\s*=>\s*(\$\d+|\?)\s*\)",
        r"datetime('now', '-' || \1 || ' days')",
        sql,
        flags=re.IGNORECASE
    )
    sql = re.sub(
        r"INTERVAL\s+'(\d+)\s+days'",
        r"datetime('now', '-\1 days')",
        sql,
        flags=re.IGNORECASE
    )

    # 5. Translate NOW()
    sql = re.sub(r'\bNOW\(\)', "datetime('now')", sql, flags=re.IGNORECASE)

    # 6. Translate CURRENT_DATE
    sql = re.sub(r'\bCURRENT_DATE\b', "date('now')", sql, flags=re.IGNORECASE)

    # 7. Translate $1, $2 ... to ?
    sql = re.sub(r'\$\d+', '?', sql)

    return sql


def _sanitize_args(args: tuple) -> tuple:
    sanitized = []
    for a in args:
        if isinstance(a, (date, datetime)):
            sanitized.append(a.isoformat())
        else:
            sanitized.append(a)
    return tuple(sanitized)


class SQLiteTransaction:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    async def __aenter__(self):
        try:
            self.conn.execute("BEGIN TRANSACTION;")
        except sqlite3.OperationalError:
            pass
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self.conn.execute("ROLLBACK;")
            except Exception:
                pass
        else:
            try:
                self.conn.execute("COMMIT;")
            except Exception:
                pass


class SQLiteConnection:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def transaction(self) -> SQLiteTransaction:
        return SQLiteTransaction(self.conn)

    async def execute(self, query: str, *args) -> str:
        translated = _translate_query(query)
        clean_args = _sanitize_args(args)
        # Handle multiple statements (e.g. migration script)
        if ";" in translated and not clean_args:
            self.conn.executescript(translated)
            return "SUCCESS"

        cursor = self.conn.cursor()
        try:
            cursor.execute(translated, clean_args)
        except sqlite3.IntegrityError as e:
            raise asyncpg.UniqueViolationError(str(e))
        except sqlite3.OperationalError as e:
            if "unique" in str(e).lower():
                raise asyncpg.UniqueViolationError(str(e))
            raise

        rowcount = cursor.rowcount
        self.conn.commit()

        q_upper = query.strip().upper()
        if q_upper.startswith("UPDATE"):
            return f"UPDATE {max(1, rowcount)}"
        if q_upper.startswith("DELETE"):
            return f"DELETE {max(1, rowcount)}"
        if q_upper.startswith("INSERT"):
            return f"INSERT {max(1, rowcount)}"
        return "SUCCESS"

    async def fetch(self, query: str, *args) -> List[SQLiteRecord]:
        translated = _translate_query(query)
        clean_args = _sanitize_args(args)
        cursor = self.conn.cursor()
        cursor.execute(translated, clean_args)
        rows = cursor.fetchall()
        return [_convert_row(cursor, r) for r in rows]

    async def fetchrow(self, query: str, *args) -> Optional[SQLiteRecord]:
        translated = _translate_query(query)
        clean_args = _sanitize_args(args)
        cursor = self.conn.cursor()
        cursor.execute(translated, clean_args)
        row = cursor.fetchone()
        return _convert_row(cursor, row) if row else None

    async def fetchval(self, query: str, *args) -> Any:
        translated = _translate_query(query)
        clean_args = _sanitize_args(args)
        cursor = self.conn.cursor()
        cursor.execute(translated, clean_args)
        row = cursor.fetchone()
        return row[0] if row else None


class SQLiteAcquireContext:
    def __init__(self, pool: "SQLitePool"):
        self.pool = pool

    async def __aenter__(self) -> SQLiteConnection:
        return SQLiteConnection(self.pool.conn)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class SQLitePool:
    def __init__(self, db_path: str = "levelup.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30.0,
            autocommit=True
        )
        self.conn.execute("PRAGMA foreign_keys = ON;")
        if db_path != ":memory:":
            self.conn.execute("PRAGMA journal_mode = WAL;")

    def acquire(self) -> SQLiteAcquireContext:
        return SQLiteAcquireContext(self)

    async def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
