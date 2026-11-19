import pytest
from unittest.mock import AsyncMock
from app.services.achievements import AchievementService
from app.database.models import Achievement


@pytest.mark.asyncio
async def test_check_registration(mock_bot):
    ach_repo = AsyncMock()
    first_step_ach = Achievement(
        id=1,
        code="first_step",
        title="First Step",
        description="Первый шаг",
        icon="🚀",
        xp_requirement=0,
        condition_type="registration",
        condition_value=1,
        reward_xp=10
    )
    ach_repo.get_by_code.return_value = first_step_ach
    ach_repo.unlock.return_value = True

    xp_service = AsyncMock()
    service = AchievementService(achievement_repo=ach_repo, xp_service=xp_service)

    await service.check_registration(123456, bot=mock_bot)

    ach_repo.unlock.assert_awaited_once_with(123456, 1)
    xp_service.award_xp.assert_awaited_once()
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_xp_and_level_experienced(mock_bot):
    ach_repo = AsyncMock()
    exp_ach = Achievement(
        id=2,
        code="experienced",
        title="Experienced",
        description="1000 XP",
        icon="⚡",
        xp_requirement=1000,
        condition_type="total_xp",
        condition_value=1000,
        reward_xp=100
    )
    ach_repo.get_by_code.return_value = exp_ach
    ach_repo.unlock.return_value = True

    xp_service = AsyncMock()
    service = AchievementService(achievement_repo=ach_repo, xp_service=xp_service)

    # 500 XP -> no unlock
    await service.check_xp_and_level(123, total_xp=500, level=5, bot=mock_bot)
    ach_repo.unlock.assert_not_awaited()

    # 1050 XP -> unlocks
    await service.check_xp_and_level(123, total_xp=1050, level=11, bot=mock_bot)
    assert ach_repo.unlock.await_count >= 1


@pytest.mark.asyncio
async def test_render_achievements_text():
    from app.handlers.achievements import render_achievements_text
    from datetime import datetime, timezone

    ach_repo = AsyncMock()
    ach1 = Achievement(
        id=1,
        code="first_step",
        title="First Step",
        description="Первый шаг",
        icon="🚀",
        xp_requirement=0,
        condition_type="registration",
        condition_value=1,
        reward_xp=10
    )
    ach_repo.list_all.return_value = [ach1]
    ach_repo.get_user_achievements_with_details.return_value = [
        (ach1, datetime.now(timezone.utc))
    ]

    text = await render_achievements_text(12345, ach_repo)
    assert "ДОСТИЖЕНИЯ" in text
    assert "First Step" in text
    assert "Разблокировано" in text
