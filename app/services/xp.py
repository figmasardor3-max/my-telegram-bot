import logging
import uuid
from typing import Optional, Tuple
from aiogram import Bot
from app.database.repositories.xp import XPRepository
from app.services.levels import LevelService

logger = logging.getLogger(__name__)


class XPService:
    def __init__(self, xp_repo: XPRepository, achievement_service=None):
        self.xp_repo = xp_repo
        self.achievement_service = achievement_service

    def set_achievement_service(self, achievement_service):
        self.achievement_service = achievement_service

    async def award_xp(
        self,
        user_id: int,
        amount: int,
        reason: str,
        idempotency_key: Optional[str] = None,
        bot: Optional[Bot] = None
    ) -> Tuple[bool, int, int, bool]:
        """
        Awards XP to a user with idempotency protection and level-up detection.
        Returns: (awarded, new_xp, new_level, level_up)
        """
        if amount <= 0:
            logger.warning(f"Attempted to award non-positive XP ({amount}) to user {user_id}")
            return False, 0, 0, False

        if not idempotency_key:
            idempotency_key = f"xp_{user_id}_{uuid.uuid4().hex}"

        awarded, new_xp, new_level, level_up = await self.xp_repo.add_xp_with_transaction(
            user_id=user_id,
            amount=amount,
            reason=reason,
            idempotency_key=idempotency_key
        )

        if not awarded:
            logger.info(f"Duplicate XP award skipped for user {user_id} (key: {idempotency_key})")
            return False, new_xp, new_level, False

        # If level increased and bot instance provided, notify user
        if level_up and bot:
            try:
                progress_bar = LevelService.render_progress_bar(new_xp % 100, 100)
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⚡ <b>НОВЫЙ УРОВЕНЬ ДОСТИГНУТ!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"Поздравляем! Ваш уровень повышен до <b>LEVEL {new_level:02d}</b>\n\n"
                        f"Всего XP: <b>{new_xp}</b>\n"
                        f"Прогресс: <code>[{progress_bar}]</code>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"<i>Продолжайте выполнять задания и поднимайтесь в рейтинге!</i>"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to send level-up notification to {user_id}: {e}")

        # Check XP and Level achievements
        if self.achievement_service:
            try:
                await self.achievement_service.check_xp_and_level(user_id, new_xp, new_level, bot)
            except Exception as e:
                logger.error(f"Error checking achievements after XP award: {e}")

        return True, new_xp, new_level, level_up

    async def deduct_xp(
        self,
        user_id: int,
        amount: int,
        reason: str,
        bot: Optional[Bot] = None
    ) -> Tuple[bool, int, int]:
        """
        Admin deduction of XP. User XP will not drop below 0.
        """
        if amount <= 0:
            return False, 0, 0

        idempotency_key = f"deduct_{user_id}_{uuid.uuid4().hex}"
        awarded, new_xp, new_level, _ = await self.xp_repo.add_xp_with_transaction(
            user_id=user_id,
            amount=-amount,
            reason=f"[ADMIN DEDUCT] {reason}",
            idempotency_key=idempotency_key
        )

        if bot:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"⚠️ <b>КОРРЕКТИРОВКА ОПЫТА</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"С вашего баланса списано: <b>-{amount} XP</b>\n"
                        f"Причина: <i>{reason}</i>\n"
                        f"Текущий уровень: <b>LEVEL {new_level:02d}</b> ({new_xp} XP)\n"
                        f"━━━━━━━━━━━━━━━━━━━"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Failed to notify user {user_id} of XP deduction: {e}")

        return awarded, new_xp, new_level
