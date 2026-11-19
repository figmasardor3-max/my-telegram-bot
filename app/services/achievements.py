import logging
from typing import Optional, List, Tuple
from aiogram import Bot
from app.database.models import Achievement
from app.database.repositories.achievements import AchievementRepository

logger = logging.getLogger(__name__)


class AchievementService:
    def __init__(self, achievement_repo: AchievementRepository, xp_service=None):
        self.achievement_repo = achievement_repo
        self.xp_service = xp_service

    def set_xp_service(self, xp_service):
        self.xp_service = xp_service

    async def _unlock_and_notify(
        self,
        user_id: int,
        achievement: Achievement,
        bot: Optional[Bot] = None
    ) -> bool:
        """Helper to safely unlock achievement, grant bonus XP, and notify."""
        unlocked = await self.achievement_repo.unlock(user_id, achievement.id)
        if not unlocked:
            return False

        logger.info(f"User {user_id} unlocked achievement: {achievement.code} ({achievement.title})")

        # Grant reward XP if achievement has a bonus
        if achievement.reward_xp > 0 and self.xp_service:
            idempotency_key = f"achievement_{user_id}_{achievement.code}"
            await self.xp_service.award_xp(
                user_id=user_id,
                amount=achievement.reward_xp,
                reason=f"Достижение: {achievement.title}",
                idempotency_key=idempotency_key,
                bot=bot
            )

        if bot:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"🎖 <b>НОВОЕ ДОСТИЖЕНИЕ РАЗБЛОКИРОВАНО!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"{achievement.icon} <b>{achievement.title}</b>\n"
                        f"<i>{achievement.description}</i>\n\n"
                        f"Награда: <b>+{achievement.reward_xp} XP</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not send achievement notification to {user_id}: {e}")

        return True

    async def check_registration(self, user_id: int, bot: Optional[Bot] = None) -> None:
        """Checks and unlocks First Step achievement upon registration."""
        ach = await self.achievement_repo.get_by_code("first_step")
        if ach:
            await self._unlock_and_notify(user_id, ach, bot)

    async def check_daily_streak(
        self, user_id: int, total_claims: int, bot: Optional[Bot] = None
    ) -> None:
        """Checks Active User achievement (7 days)."""
        if total_claims >= 7:
            ach = await self.achievement_repo.get_by_code("active_user")
            if ach:
                await self._unlock_and_notify(user_id, ach, bot)

    async def check_xp_and_level(
        self, user_id: int, total_xp: int, level: int, bot: Optional[Bot] = None
    ) -> None:
        """Checks XP (1000) and Level (10) achievements."""
        if total_xp >= 1000:
            ach = await self.achievement_repo.get_by_code("experienced")
            if ach:
                await self._unlock_and_notify(user_id, ach, bot)

        if level >= 10:
            ach = await self.achievement_repo.get_by_code("rising_star")
            if ach:
                await self._unlock_and_notify(user_id, ach, bot)

    async def check_referrals(
        self, user_id: int, referrals_count: int, bot: Optional[Bot] = None
    ) -> None:
        """Checks Social achievement (5 referrals)."""
        if referrals_count >= 5:
            ach = await self.achievement_repo.get_by_code("social")
            if ach:
                await self._unlock_and_notify(user_id, ach, bot)

    async def check_completed_tasks(
        self, user_id: int, tasks_count: int, bot: Optional[Bot] = None
    ) -> None:
        """Checks Task Hunter achievement (10 tasks)."""
        if tasks_count >= 10:
            ach = await self.achievement_repo.get_by_code("task_hunter")
            if ach:
                await self._unlock_and_notify(user_id, ach, bot)
