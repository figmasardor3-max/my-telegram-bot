import logging
from typing import List, Optional, Tuple
from datetime import datetime
import asyncpg
from app.database.models import XPEvent, LeaderboardEntry

logger = logging.getLogger(__name__)


class XPRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_event(self, row: asyncpg.Record) -> XPEvent:
        return XPEvent(
            id=row["id"],
            user_id=row["user_id"],
            amount=row["amount"],
            reason=row["reason"],
            created_at=row["created_at"],
            idempotency_key=row["idempotency_key"]
        )

    async def add_xp_with_transaction(
        self,
        user_id: int,
        amount: int,
        reason: str,
        idempotency_key: str
    ) -> Tuple[bool, int, int, bool]:
        """
        Atomically records an XP event and updates user's XP and Level.
        Returns: (success, new_xp, new_level, level_up)
        If idempotency_key already exists, returns (False, current_xp, current_level, False)
        """
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # 1. Check idempotency
                existing = await conn.fetchval(
                    "SELECT 1 FROM xp_events WHERE idempotency_key = $1;",
                    idempotency_key
                )
                if existing:
                    user_row = await conn.fetchrow(
                        "SELECT xp, level FROM users WHERE telegram_id = $1;",
                        user_id
                    )
                    curr_xp = user_row["xp"] if user_row else 0
                    curr_lvl = user_row["level"] if user_row else 1
                    return False, curr_xp, curr_lvl, False

                # 2. Fetch current user data with lock
                user_row = await conn.fetchrow(
                    "SELECT xp, level FROM users WHERE telegram_id = $1 FOR UPDATE;",
                    user_id
                )
                if not user_row:
                    raise ValueError(f"User {user_id} not found")

                old_xp = user_row["xp"]
                old_level = user_row["level"]

                # 3. Calculate new xp and level
                new_xp = max(0, old_xp + amount)
                new_level = (new_xp // 100) + 1
                level_up = new_level > old_level

                # 4. Insert event
                await conn.execute(
                    """
                    INSERT INTO xp_events (user_id, amount, reason, idempotency_key)
                    VALUES ($1, $2, $3, $4);
                    """,
                    user_id, amount, reason, idempotency_key
                )

                # 5. Update user
                await conn.execute(
                    """
                    UPDATE users
                    SET xp = $1, level = $2, last_active_at = NOW()
                    WHERE telegram_id = $3;
                    """,
                    new_xp, new_level, user_id
                )

                return True, new_xp, new_level, level_up

    async def get_history(self, user_id: int, limit: int = 10) -> List[XPEvent]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM xp_events
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2;
                """,
                user_id, limit
            )
            return [self._row_to_event(r) for r in rows]

    async def get_total_xp_distributed(self) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COALESCE(SUM(amount), 0) FROM xp_events WHERE amount > 0;"
            )
            return int(val or 0)

    async def get_global_leaderboard(self, limit: int = 10) -> List[LeaderboardEntry]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT telegram_id, first_name, username, level, xp, selected_badge,
                       ROW_NUMBER() OVER (ORDER BY xp DESC, created_at ASC) as rank
                FROM users
                ORDER BY rank ASC
                LIMIT $1;
                """,
                limit
            )
            return [
                LeaderboardEntry(
                    rank=int(r["rank"]),
                    telegram_id=r["telegram_id"],
                    first_name=r["first_name"],
                    username=r["username"],
                    level=r["level"],
                    xp=r["xp"],
                    selected_badge=r["selected_badge"] or "⚡"
                )
                for r in rows
            ]

    async def get_period_leaderboard(self, days: int, limit: int = 10) -> List[LeaderboardEntry]:
        """Leaderboard based on XP earned within the last N days."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH period_xp AS (
                    SELECT user_id, COALESCE(SUM(amount), 0) AS period_score
                    FROM xp_events
                    WHERE created_at >= NOW() - make_interval(days => $1)
                      AND amount > 0
                    GROUP BY user_id
                )
                SELECT u.telegram_id, u.first_name, u.username, u.level,
                       COALESCE(px.period_score, 0) AS xp,
                       u.selected_badge,
                       ROW_NUMBER() OVER (ORDER BY COALESCE(px.period_score, 0) DESC, u.created_at ASC) as rank
                FROM users u
                INNER JOIN period_xp px ON u.telegram_id = px.user_id
                WHERE px.period_score > 0
                ORDER BY rank ASC
                LIMIT $2;
                """,
                days, limit
            )
            return [
                LeaderboardEntry(
                    rank=int(r["rank"]),
                    telegram_id=r["telegram_id"],
                    first_name=r["first_name"],
                    username=r["username"],
                    level=r["level"],
                    xp=int(r["xp"]),
                    selected_badge=r["selected_badge"] or "⚡"
                )
                for r in rows
            ]

    async def get_user_period_stats(self, user_id: int, days: int) -> Tuple[int, int]:
        """Returns (rank, period_score) for a specific user over the last N days."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                WITH period_scores AS (
                    SELECT u.telegram_id,
                           COALESCE(SUM(e.amount), 0) AS score,
                           ROW_NUMBER() OVER (ORDER BY COALESCE(SUM(e.amount), 0) DESC, u.created_at ASC) as rnk
                    FROM users u
                    LEFT JOIN xp_events e ON u.telegram_id = e.user_id
                        AND e.created_at >= NOW() - make_interval(days => $1)
                        AND e.amount > 0
                    GROUP BY u.telegram_id, u.created_at
                )
                SELECT rnk, score FROM period_scores WHERE telegram_id = $2;
                """,
                days, user_id
            )
            if row:
                return int(row["rnk"]), int(row["score"])
            return 1, 0
