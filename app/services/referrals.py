import logging
import secrets
from typing import Optional, Tuple
from aiogram import Bot
from app.database.repositories.referrals import ReferralRepository
from app.database.repositories.users import UserRepository
from app.services.xp import XPService

logger = logging.getLogger(__name__)


class ReferralService:
    INVITER_BONUS_XP: int = 50

    def __init__(
        self,
        referral_repo: ReferralRepository,
        user_repo: UserRepository,
        xp_service: XPService,
        achievement_service=None
    ):
        self.referral_repo = referral_repo
        self.user_repo = user_repo
        self.xp_service = xp_service
        self.achievement_service = achievement_service

    def set_achievement_service(self, achievement_service):
        self.achievement_service = achievement_service

    @staticmethod
    def generate_referral_code() -> str:
        """Generates an 8-character unique alphanumeric referral code."""
        return secrets.token_hex(4).upper()

    async def process_referral_registration(
        self,
        new_user_id: int,
        new_user_name: str,
        referral_code: str,
        bot: Optional[Bot] = None
    ) -> Optional[int]:
        """
        Processes referral code when a new user registers.
        Returns inviter_id if valid, None otherwise.
        """
        inviter = await self.user_repo.get_by_referral_code(referral_code)
        if not inviter:
            return None

        # Prevent self-invite
        if inviter.telegram_id == new_user_id:
            logger.warning(f"User {new_user_id} attempted self-referral.")
            return None

        # Record referral
        added = await self.referral_repo.add_referral(inviter.telegram_id, new_user_id)
        if not added:
            return None

        # Award inviter bonus XP
        idempotency_key = f"ref_{inviter.telegram_id}_{new_user_id}"
        await self.xp_service.award_xp(
            user_id=inviter.telegram_id,
            amount=self.INVITER_BONUS_XP,
            reason=f"Реферал: новый участник {new_user_name}",
            idempotency_key=idempotency_key,
            bot=bot
        )
        await self.referral_repo.mark_as_rewarded(inviter.telegram_id, new_user_id)

        # Notify inviter
        if bot:
            try:
                await bot.send_message(
                    chat_id=inviter.telegram_id,
                    text=(
                        f"👥 <b>НОВЫЙ РЕФЕРАЛ!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"По вашей ссылке зарегистрировался пользователь <b>{new_user_name}</b>!\n"
                        f"Вам начислено: <b>+{self.INVITER_BONUS_XP} XP</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Could not notify inviter {inviter.telegram_id}: {e}")

        # Check Social achievement
        ref_count = await self.referral_repo.get_referrals_count(inviter.telegram_id)
        if self.achievement_service:
            try:
                await self.achievement_service.check_referrals(inviter.telegram_id, ref_count, bot)
            except Exception as e:
                logger.error(f"Error checking referrals achievement for {inviter.telegram_id}: {e}")

        return inviter.telegram_id
