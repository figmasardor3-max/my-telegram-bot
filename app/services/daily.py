import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any
import pytz
from aiogram import Bot
from app.database.repositories.daily import DailyRepository
from app.services.xp import XPService

logger = logging.getLogger(__name__)


class DailyService:
    DAILY_XP_AMOUNT: int = 20

    def __init__(
        self,
        daily_repo: DailyRepository,
        xp_service: XPService,
        achievement_service=None,
        timezone_name: str = "Asia/Tashkent"
    ):
        self.daily_repo = daily_repo
        self.xp_service = xp_service
        self.achievement_service = achievement_service
        self.tz = pytz.timezone(timezone_name)

    def set_achievement_service(self, achievement_service):
        self.achievement_service = achievement_service

    def get_user_now(self) -> datetime:
        return datetime.now(self.tz)

    def format_dt(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(self.tz).strftime("%d.%m.%Y %H:%M")

    async def get_daily_status(self, user_id: int) -> Dict[str, Any]:
        """
        Calculates daily claim status, remaining cooldown time until next UTC midnight,
        and total claims count.
        """
        today_claim = await self.daily_repo.get_today_claim(user_id)
        total_claims = await self.daily_repo.get_total_claims_count(user_id)
        last_claim = await self.daily_repo.get_last_claim(user_id)

        now_utc = datetime.now(timezone.utc)
        # Next claim becomes available at next 00:00:00 UTC
        next_claim_utc = datetime(
            now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc
        ) + timedelta(days=1)

        time_left = next_claim_utc - now_utc
        hours, remainder = divmod(int(time_left.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        next_available_local_str = next_claim_utc.astimezone(self.tz).strftime("%d.%m.%Y %H:%M")

        return {
            "can_claim": today_claim is None,
            "total_claims": total_claims,
            "last_claim_at": self.format_dt(last_claim.created_at) if last_claim else "Никогда",
            "next_available_str": next_available_local_str,
            "time_left_str": f"{hours:02d}ч {minutes:02d}мин",
            "reward_xp": self.DAILY_XP_AMOUNT
        }

    async def claim_daily_reward(
        self, user_id: int, bot: Optional[Bot] = None
    ) -> Tuple[bool, str, int]:
        """
        Attempts to claim daily reward.
        Returns: (success: bool, message: str, awarded_xp: int)
        """
        # 1. Try to record claim for today (UTC)
        recorded = await self.daily_repo.record_claim(user_id, self.DAILY_XP_AMOUNT)
        if not recorded:
            status = await self.get_daily_status(user_id)
            return False, f"Вы уже забрали сегодняшнюю награду! Следующая через {status['time_left_str']}.", 0

        # 2. Award XP via XPService with deterministic idempotency key for this day
        today_utc_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        idempotency_key = f"daily_{user_id}_{today_utc_str}"

        awarded, new_xp, new_level, level_up = await self.xp_service.award_xp(
            user_id=user_id,
            amount=self.DAILY_XP_AMOUNT,
            reason="Ежедневная награда (Daily Reward)",
            idempotency_key=idempotency_key,
            bot=bot
        )

        total_claims = await self.daily_repo.get_total_claims_count(user_id)

        # 3. Check daily claims achievements (e.g. Active User: 7 days)
        if self.achievement_service:
            try:
                await self.achievement_service.check_daily_streak(user_id, total_claims, bot)
            except Exception as e:
                logger.error(f"Error checking daily streak achievement: {e}")

        msg = (
            f"🎁 <b>ЕЖЕДНЕВНАЯ НАГРАДА ПОЛУЧЕНА!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Начислено: <b>+{self.DAILY_XP_AMOUNT} XP</b>\n"
            f"Всего дней активности: <b>{total_claims}</b>\n"
            f"Текущий баланс: <b>{new_xp} XP</b> (LEVEL {new_level:02d})\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<i>Возвращайтесь завтра за следующей наградой!</i>"
        )
        return True, msg, self.DAILY_XP_AMOUNT
