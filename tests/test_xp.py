import pytest
from unittest.mock import AsyncMock
from app.services.xp import XPService


@pytest.mark.asyncio
async def test_award_xp_success(mock_bot):
    xp_repo = AsyncMock()
    # (awarded, new_xp, new_level, level_up)
    xp_repo.add_xp_with_transaction.return_value = (True, 150, 2, True)

    service = XPService(xp_repo=xp_repo)
    awarded, new_xp, new_level, level_up = await service.award_xp(
        user_id=123,
        amount=50,
        reason="Daily Reward",
        idempotency_key="key_1",
        bot=mock_bot
    )

    assert awarded is True
    assert new_xp == 150
    assert new_level == 2
    assert level_up is True
    # Verify level up notification was triggered
    mock_bot.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_award_xp_idempotency_skip(mock_bot):
    xp_repo = AsyncMock()
    # Duplicate returns False
    xp_repo.add_xp_with_transaction.return_value = (False, 100, 2, False)

    service = XPService(xp_repo=xp_repo)
    awarded, new_xp, new_level, level_up = await service.award_xp(
        user_id=123,
        amount=50,
        reason="Daily Reward",
        idempotency_key="key_1",
        bot=mock_bot
    )

    assert awarded is False
    assert new_xp == 100
    mock_bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_award_zero_or_negative_xp():
    xp_repo = AsyncMock()
    service = XPService(xp_repo=xp_repo)

    awarded, new_xp, new_level, level_up = await service.award_xp(
        user_id=123,
        amount=0,
        reason="Invalid",
    )
    assert awarded is False
    xp_repo.add_xp_with_transaction.assert_not_awaited()
