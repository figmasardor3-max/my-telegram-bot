from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
import asyncpg
from app.database.repositories import (
    UserRepository,
    XPRepository,
    DailyRepository,
    TaskRepository,
    AchievementRepository,
    ReferralRepository,
)
from app.services import (
    XPService,
    DailyService,
    TaskService,
    AchievementService,
    ReferralService,
)


class DatabaseMiddleware(BaseMiddleware):
    def __init__(
        self,
        pool: asyncpg.Pool,
        user_repo: UserRepository,
        xp_repo: XPRepository,
        daily_repo: DailyRepository,
        task_repo: TaskRepository,
        achievement_repo: AchievementRepository,
        referral_repo: ReferralRepository,
        xp_service: XPService,
        daily_service: DailyService,
        task_service: TaskService,
        achievement_service: AchievementService,
        referral_service: ReferralService,
    ):
        super().__init__()
        self.pool = pool
        self.user_repo = user_repo
        self.xp_repo = xp_repo
        self.daily_repo = daily_repo
        self.task_repo = task_repo
        self.achievement_repo = achievement_repo
        self.referral_repo = referral_repo
        self.xp_service = xp_service
        self.daily_service = daily_service
        self.task_service = task_service
        self.achievement_service = achievement_service
        self.referral_service = referral_service

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["pool"] = self.pool
        data["user_repo"] = self.user_repo
        data["xp_repo"] = self.xp_repo
        data["daily_repo"] = self.daily_repo
        data["task_repo"] = self.task_repo
        data["achievement_repo"] = self.achievement_repo
        data["referral_repo"] = self.referral_repo

        data["xp_service"] = self.xp_service
        data["daily_service"] = self.daily_service
        data["task_service"] = self.task_service
        data["achievement_service"] = self.achievement_service
        data["referral_service"] = self.referral_service

        # Update last_active_at if event comes from a user
        tg_user: TgUser = data.get("event_from_user")
        if tg_user and not tg_user.is_bot:
            try:
                await self.user_repo.update_last_active(tg_user.id)
            except Exception:
                pass

        return await handler(event, data)
