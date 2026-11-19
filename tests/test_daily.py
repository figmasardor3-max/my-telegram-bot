import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.daily import DailyService
from app.database.models import DailyClaim


@pytest.mark.asyncio
async def test_daily_status_can_claim():
    daily_repo = AsyncMock()
    daily_repo.get_today_claim.return_value = None
    daily_repo.get_total_claims_count.return_value = 3
    daily_repo.get_last_claim.return_value = None

    xp_service = AsyncMock()
    service = DailyService(
        daily_repo=daily_repo,
        xp_service=xp_service,
        timezone_name="Asia/Tashkent"
    )

    status = await service.get_daily_status(12345)
    assert status["can_claim"] is True
    assert status["total_claims"] == 3
    assert status["reward_xp"] == 20
    assert "time_left_str" in status


@pytest.mark.asyncio
async def test_claim_daily_already_claimed():
    daily_repo = AsyncMock()
    daily_repo.record_claim.return_value = False  # Duplicate claim rejected
    daily_repo.get_today_claim.return_value = MagicMock()
    daily_repo.get_total_claims_count.return_value = 1
    daily_repo.get_last_claim.return_value = None

    xp_service = AsyncMock()
    service = DailyService(
        daily_repo=daily_repo,
        xp_service=xp_service
    )

    success, msg, xp = await service.claim_daily_reward(12345)
    assert success is False
    assert xp == 0
    assert "уже забрали" in msg
    xp_service.award_xp.assert_not_awaited()


@pytest.mark.asyncio
async def test_claim_daily_success(mock_bot):
    daily_repo = AsyncMock()
    daily_repo.record_claim.return_value = True
    daily_repo.get_total_claims_count.return_value = 1
    daily_repo.get_last_claim.return_value = None

    xp_service = AsyncMock()
    xp_service.award_xp.return_value = (True, 120, 2, False)

    service = DailyService(
        daily_repo=daily_repo,
        xp_service=xp_service
    )

    success, msg, xp = await service.claim_daily_reward(12345, bot=mock_bot)
    assert success is True
    assert xp == 20
    assert "ЕЖЕДНЕВНАЯ НАГРАДА ПОЛУЧЕНА" in msg
    xp_service.award_xp.assert_awaited_once()
