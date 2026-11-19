from datetime import datetime
from typing import Optional, List, Dict, Any
import asyncpg
from app.database.models import User


class UserRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_user(self, row: asyncpg.Record) -> User:
        return User(
            id=row["id"],
            telegram_id=row["telegram_id"],
            username=row["username"],
            first_name=row["first_name"],
            xp=row["xp"],
            level=row["level"],
            referral_code=row["referral_code"],
            referred_by=row["referred_by"],
            selected_title=row.get("selected_title") or "Новичок",
            selected_badge=row.get("selected_badge") or "⚡",
            created_at=row["created_at"],
            last_active_at=row["last_active_at"],
        )

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE telegram_id = $1;",
                telegram_id
            )
            return self._row_to_user(row) if row else None

    async def get_by_referral_code(self, referral_code: str) -> Optional[User]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE referral_code = $1;",
                referral_code
            )
            return self._row_to_user(row) if row else None

    async def create_user(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: str,
        referral_code: str,
        referred_by: Optional[int] = None
    ) -> User:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (telegram_id, username, first_name, referral_code, referred_by, xp, level)
                VALUES ($1, $2, $3, $4, $5, 0, 1)
                ON CONFLICT (telegram_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_active_at = NOW()
                RETURNING *;
                """,
                telegram_id, username, first_name, referral_code, referred_by
            )
            return self._row_to_user(row)

    async def update_last_active(self, telegram_id: int) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_active_at = NOW() WHERE telegram_id = $1;",
                telegram_id
            )

    async def update_customization(
        self,
        telegram_id: int,
        title: Optional[str] = None,
        badge: Optional[str] = None
    ) -> None:
        async with self.pool.acquire() as conn:
            if title and badge:
                await conn.execute(
                    "UPDATE users SET selected_title = $1, selected_badge = $2 WHERE telegram_id = $3;",
                    title, badge, telegram_id
                )
            elif title:
                await conn.execute(
                    "UPDATE users SET selected_title = $1 WHERE telegram_id = $2;",
                    title, telegram_id
                )
            elif badge:
                await conn.execute(
                    "UPDATE users SET selected_badge = $1 WHERE telegram_id = $2;",
                    badge, telegram_id
                )

    async def get_user_rank(self, telegram_id: int) -> int:
        """Returns 1-based rank by total XP, breaking ties by registration date."""
        async with self.pool.acquire() as conn:
            rank = await conn.fetchval(
                """
                WITH ranked AS (
                    SELECT telegram_id,
                           ROW_NUMBER() OVER (ORDER BY xp DESC, created_at ASC) as rnk
                    FROM users
                )
                SELECT rnk FROM ranked WHERE telegram_id = $1;
                """,
                telegram_id
            )
            return int(rank) if rank is not None else 1

    async def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Aggregate all stats for profile view."""
        async with self.pool.acquire() as conn:
            user = await self.get_by_telegram_id(telegram_id)
            if not user:
                return {}

            rank = await self.get_user_rank(telegram_id)

            completed_tasks = await conn.fetchval(
                "SELECT COUNT(*) FROM user_tasks WHERE user_id = $1;",
                telegram_id
            )

            achievements_count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_achievements WHERE user_id = $1;",
                telegram_id
            )

            referrals_count = await conn.fetchval(
                "SELECT COUNT(*) FROM referrals WHERE inviter_id = $1;",
                telegram_id
            )

            return {
                "user": user,
                "rank": rank,
                "completed_tasks": completed_tasks or 0,
                "achievements_count": achievements_count or 0,
                "referrals_count": referrals_count or 0,
            }

    async def get_total_users_count(self) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("SELECT COUNT(*) FROM users;")
            return int(val or 0)

    async def get_new_users_today_count(self) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE created_at >= CURRENT_DATE;"
            )
            return int(val or 0)

    async def get_active_users_week_count(self) -> int:
        async with self.pool.acquire() as conn:
            val = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE last_active_at >= NOW() - INTERVAL '7 days';"
            )
            return int(val or 0)

    async def get_all_telegram_ids(self) -> List[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT telegram_id FROM users;")
            return [row["telegram_id"] for row in rows]
