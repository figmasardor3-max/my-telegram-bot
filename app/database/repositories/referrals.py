from datetime import datetime
from typing import Optional, List
import asyncpg
from app.database.models import Referral


class ReferralRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_referral(self, row: asyncpg.Record) -> Referral:
        return Referral(
            id=row["id"],
            inviter_id=row["inviter_id"],
            invited_id=row["invited_id"],
            created_at=row["created_at"],
            rewarded=row["rewarded"]
        )

    async def add_referral(self, inviter_id: int, invited_id: int) -> bool:
        """
        Records that invited_id was referred by inviter_id.
        Prevents self-referral and duplicate invites.
        """
        if inviter_id == invited_id:
            return False

        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO referrals (inviter_id, invited_id, created_at, rewarded)
                    VALUES ($1, $2, NOW(), FALSE);
                    """,
                    inviter_id, invited_id
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def get_referrals_count(self, inviter_id: int) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE inviter_id = $1;",
                inviter_id
            )
            return int(val or 0)

    async def get_referrals_list(self, inviter_id: int, limit: int = 20) -> List[Referral]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM referrals
                WHERE inviter_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                inviter_id, limit
            )
            return [self._row_to_referral(r) for r in rows]

    async def mark_as_rewarded(self, inviter_id: int, invited_id: int) -> bool:
        async with self.pool.acquire() as conn:
            res = await conn.execute(
                """
                UPDATE referrals
                SET rewarded = TRUE
                WHERE inviter_id = $1 AND invited_id = $2 AND rewarded = FALSE;
                """,
                inviter_id, invited_id
            )
            return "UPDATE 1" in res
