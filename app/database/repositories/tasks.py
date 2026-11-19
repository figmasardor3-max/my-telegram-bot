from datetime import datetime
from typing import Optional, List, Set
import asyncpg
from app.database.models import Task, UserTask


class TaskRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    def _row_to_task(self, row: asyncpg.Record) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            category=row["category"],
            reward_xp=row["reward_xp"],
            condition_type=row.get("condition_type", "manual"),
            condition_target=row.get("condition_target", 1),
            expires_at=row["expires_at"],
            is_active=row["is_active"],
            created_at=row["created_at"]
        )

    def _row_to_user_task(self, row: asyncpg.Record) -> UserTask:
        return UserTask(
            id=row["id"],
            user_id=row["user_id"],
            task_id=row["task_id"],
            status=row["status"],
            completed_at=row["completed_at"],
            rewarded_at=row["rewarded_at"]
        )

    async def list_active_tasks(self, category: Optional[str] = None) -> List[Task]:
        async with self.pool.acquire() as conn:
            if category:
                rows = await conn.fetch(
                    """
                    SELECT * FROM tasks
                    WHERE is_active = TRUE AND category = $1
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY id ASC;
                    """,
                    category
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM tasks
                    WHERE is_active = TRUE
                      AND (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY category ASC, id ASC;
                    """
                )
            return [self._row_to_task(r) for r in rows]

    async def get_all_tasks_admin(self) -> List[Task]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM tasks ORDER BY id DESC;")
            return [self._row_to_task(r) for r in rows]

    async def get_by_id(self, task_id: int) -> Optional[Task]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM tasks WHERE id = $1;", task_id)
            return self._row_to_task(row) if row else None

    async def get_user_task(self, user_id: int, task_id: int) -> Optional[UserTask]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_tasks WHERE user_id = $1 AND task_id = $2;",
                user_id, task_id
            )
            return self._row_to_user_task(row) if row else None

    async def get_completed_task_ids(self, user_id: int) -> Set[int]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT task_id FROM user_tasks WHERE user_id = $1;",
                user_id
            )
            return {r["task_id"] for r in rows}

    async def mark_completed(self, user_id: int, task_id: int) -> bool:
        """Records task completion for the user. Returns True if inserted, False if already exists."""
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO user_tasks (user_id, task_id, status, completed_at, rewarded_at)
                    VALUES ($1, $2, 'completed', NOW(), NOW());
                    """,
                    user_id, task_id
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def create_task(
        self,
        title: str,
        description: str,
        category: str,
        reward_xp: int,
        condition_type: str = "manual",
        condition_target: int = 1,
        expires_at: Optional[datetime] = None
    ) -> Task:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tasks (title, description, category, reward_xp, condition_type, condition_target, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *;
                """,
                title, description, category, reward_xp, condition_type, condition_target, expires_at
            )
            return self._row_to_task(row)

    async def toggle_active(self, task_id: int) -> bool:
        async with self.pool.acquire() as conn:
            new_state = await conn.fetchval(
                """
                UPDATE tasks
                SET is_active = NOT is_active
                WHERE id = $1
                RETURNING is_active;
                """,
                task_id
            )
            return bool(new_state)

    async def delete_task(self, task_id: int) -> bool:
        async with self.pool.acquire() as conn:
            res = await conn.execute("DELETE FROM tasks WHERE id = $1;", task_id)
            return "DELETE 1" in res
