import pytest
from unittest.mock import AsyncMock
from datetime import datetime, timezone
from app.services.tasks import TaskService
from app.database.models import Task, User


@pytest.mark.asyncio
async def test_task_condition_reach_level(sample_user):
    task = Task(
        id=1,
        title="Восхождение",
        description="Достигните 5 уровня",
        category="weekly",
        reward_xp=50,
        condition_type="reach_level",
        condition_target=5,
        expires_at=None,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    service = TaskService(
        task_repo=AsyncMock(),
        user_repo=AsyncMock(),
        daily_repo=AsyncMock(),
        referral_repo=AsyncMock(),
        xp_service=AsyncMock()
    )

    # User level is 2, target is 5 -> should fail
    can_complete, msg = await service.check_task_completion_condition(sample_user, task)
    assert can_complete is False
    assert "ниже требуемого" in msg

    # If user level is 5 -> should pass
    sample_user.level = 5
    can_complete, msg = await service.check_task_completion_condition(sample_user, task)
    assert can_complete is True


@pytest.mark.asyncio
async def test_task_condition_daily_claim(sample_user):
    task = Task(
        id=2,
        title="Ежедневный вход",
        description="Заберите бонус",
        category="daily",
        reward_xp=20,
        condition_type="daily_claim",
        condition_target=1,
        expires_at=None,
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )

    daily_repo = AsyncMock()
    daily_repo.get_today_claim.return_value = None  # Not claimed yet

    service = TaskService(
        task_repo=AsyncMock(),
        user_repo=AsyncMock(),
        daily_repo=daily_repo,
        referral_repo=AsyncMock(),
        xp_service=AsyncMock()
    )

    can_complete, msg = await service.check_task_completion_condition(sample_user, task)
    assert can_complete is False
    assert "Сначала заберите" in msg

    # When claimed
    daily_repo.get_today_claim.return_value = AsyncMock()
    can_complete, msg = await service.check_task_completion_condition(sample_user, task)
    assert can_complete is True
