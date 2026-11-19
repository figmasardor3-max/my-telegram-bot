import logging
from typing import Optional, Tuple, List, Dict, Any
from aiogram import Bot
from app.database.models import Task, User
from app.database.repositories.tasks import TaskRepository
from app.database.repositories.users import UserRepository
from app.database.repositories.daily import DailyRepository
from app.database.repositories.referrals import ReferralRepository
from app.services.xp import XPService

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        user_repo: UserRepository,
        daily_repo: DailyRepository,
        referral_repo: ReferralRepository,
        xp_service: XPService,
        achievement_service=None
    ):
        self.task_repo = task_repo
        self.user_repo = user_repo
        self.daily_repo = daily_repo
        self.referral_repo = referral_repo
        self.xp_service = xp_service
        self.achievement_service = achievement_service

    def set_achievement_service(self, achievement_service):
        self.achievement_service = achievement_service

    async def get_tasks_with_status(
        self, user_id: int, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Returns all active tasks along with completion status for this user."""
        tasks = await self.task_repo.list_active_tasks(category)
        completed_ids = await self.task_repo.get_completed_task_ids(user_id)

        result = []
        for t in tasks:
            result.append({
                "task": t,
                "is_completed": t.id in completed_ids,
            })
        return result

    async def check_task_completion_condition(self, user: User, task: Task) -> Tuple[bool, str]:
        """
        Validates whether the user genuinely meets the condition for completing the task.
        """
        ctype = task.condition_type

        if ctype == "daily_claim":
            today_claim = await self.daily_repo.get_today_claim(user.telegram_id)
            if not today_claim:
                return False, "Сначала заберите ежедневную награду в профиле!"
            return True, "Условие выполнено!"

        elif ctype == "profile_check":
            # Profile visit is always fulfilled once user views the bot
            return True, "Условие выполнено!"

        elif ctype == "invite_friend":
            ref_count = await self.referral_repo.get_referrals_count(user.telegram_id)
            if ref_count < task.condition_target:
                return False, f"Необходимо пригласить друзей: {ref_count}/{task.condition_target}."
            return True, "Условие выполнено!"

        elif ctype == "reach_level":
            if user.level < task.condition_target:
                return False, f"Ваш уровень ({user.level}) ниже требуемого (LEVEL {task.condition_target})."
            return True, "Условие выполнено!"

        elif ctype in ("manual", "custom"):
            return True, "Задание подтверждено!"

        return True, "Выполнено!"

    async def complete_and_claim_task(
        self, user_id: int, task_id: int, bot: Optional[Bot] = None
    ) -> Tuple[bool, str, int]:
        """
        Validates condition, marks task completed, awards XP with idempotency.
        """
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            return False, "Задание не найдено.", 0

        if not task.is_active:
            return False, "Это задание больше не активно.", 0

        # Check if already completed
        user_task = await self.task_repo.get_user_task(user_id, task_id)
        if user_task:
            return False, "Вы уже выполнили это задание и получили награду!", 0

        user = await self.user_repo.get_by_telegram_id(user_id)
        if not user:
            return False, "Пользователь не найден.", 0

        # Verify condition
        can_complete, reason = await self.check_task_completion_condition(user, task)
        if not can_complete:
            return False, reason, 0

        # Record completion
        marked = await self.task_repo.mark_completed(user_id, task_id)
        if not marked:
            return False, "Задание уже было завершено ранее.", 0

        # Award XP
        idempotency_key = f"task_{user_id}_{task_id}"
        awarded, new_xp, new_level, _ = await self.xp_service.award_xp(
            user_id=user_id,
            amount=task.reward_xp,
            reason=f"Задание: {task.title}",
            idempotency_key=idempotency_key,
            bot=bot
        )

        # Check Task Hunter achievement
        completed_ids = await self.task_repo.get_completed_task_ids(user_id)
        if self.achievement_service:
            try:
                await self.achievement_service.check_completed_tasks(user_id, len(completed_ids), bot)
            except Exception as e:
                logger.error(f"Error checking task hunter achievement: {e}")

        msg = (
            f"🎯 <b>ЗАДАНИЕ ВЫПОЛНЕНО!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{task.title}</b>\n"
            f"Награда: <b>+{task.reward_xp} XP</b>\n"
            f"Текущий баланс: <b>{new_xp} XP</b> (LEVEL {new_level:02d})\n"
            f"━━━━━━━━━━━━━━━━━━━"
        )
        return True, msg, task.reward_xp
