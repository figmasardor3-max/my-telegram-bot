from datetime import datetime
from typing import Optional, List, Set, Tuple
import asyncpg
from app.database.models import Achievement, UserAchievement


class AchievementRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_achievement(self, row: asyncpg.Record) -> Achievement:
        return Achievement(
            id=row["id"],
            code=row["code"],
            title=row["title"],
            description=row["description"],
            icon=row.get("icon", "🎖"),
            xp_requirement=row.get("xp_requirement", 0),
            condition_type=row.get("condition_type", ""),
            condition_value=row.get("condition_value", 1),
            reward_xp=row.get("reward_xp", 50)
        )

    async def list_all(self) -> List[Achievement]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM achievements ORDER BY id ASC;")
            return [self._row_to_achievement(r) for r in rows]

    async def get_by_code(self, code: str) -> Optional[Achievement]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM achievements WHERE code = $1;", code)
            return self._row_to_achievement(row) if row else None

    async def get_by_id(self, achievement_id: int) -> Optional[Achievement]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM achievements WHERE id = $1;", achievement_id)
            return self._row_to_achievement(row) if row else None

    async def get_user_unlocked_ids(self, user_id: int) -> Set[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT achievement_id FROM user_achievements WHERE user_id = $1;",
                user_id
            )
            return {r["achievement_id"] for r in rows}

    async def get_user_achievements_with_details(
        self, user_id: int
    ) -> List[Tuple[Achievement, datetime]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT a.*, ua.unlocked_at
                FROM achievements a
                INNER JOIN user_achievements ua ON a.id = ua.achievement_id
                WHERE ua.user_id = $1
                ORDER BY ua.unlocked_at DESC;
                """,
                user_id
            )
            return [(self._row_to_achievement(r), r["unlocked_at"]) for r in rows]

    async def unlock(self, user_id: int, achievement_id: int) -> bool:
        """
        Unlocks achievement for user.
        Returns True if newly unlocked, False if already unlocked.
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO user_achievements (user_id, achievement_id, unlocked_at)
                    VALUES ($1, $2, NOW());
                    """,
                    user_id, achievement_id
                )
                return True
            except asyncpg.UniqueViolationError:
                return False
