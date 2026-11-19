from datetime import datetime, timezone, date
from typing import Optional, List, Tuple
import asyncpg
from app.database.models import DailyClaim


class DailyRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_claim(self, row: asyncpg.Record) -> DailyClaim:
        return DailyClaim(
            id=row["id"],
            user_id=row["user_id"],
            claim_date=row["claim_date"],
            xp_amount=row["xp_amount"],
            created_at=row["created_at"]
        )

    async def get_today_claim(self, user_id: int) -> Optional[DailyClaim]:
        """Checks if user has claimed daily reward today (in UTC)."""
        today_utc = datetime.now(timezone.utc).date()
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM daily_claims
                WHERE user_id = $1 AND claim_date = $2;
                """,
                user_id, today_utc
            )
            return self._row_to_claim(row) if row else None

    async def record_claim(self, user_id: int, xp_amount: int = 20) -> bool:
        """
        Records a daily claim for today (UTC).
        Returns True if newly recorded, False if already claimed today.
        """
        today_utc = datetime.now(timezone.utc).date()
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO daily_claims (user_id, claim_date, xp_amount)
                    VALUES ($1, $2, $3);
                    """,
                    user_id, today_utc, xp_amount
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_total_claims_count(self, user_id: int) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM daily_claims WHERE user_id = $1;",
                user_id
            )
            return int(val or 0)

    async def get_last_claim(self, user_id: int) -> Optional[DailyClaim]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM daily_claims
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT 1;
                """,
                user_id
            )
            return self._row_to_claim(row) if row else None

    async def get_claims_history(self, user_id: int, limit: int = 7) -> List[DailyClaim]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM daily_claims
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                user_id, limit
            )
            return [self._row_to_claim(r) for r in rows]
