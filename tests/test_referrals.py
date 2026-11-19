import pytest
from unittest.mock import AsyncMock
from app.services.referrals import ReferralService
from app.database.models import User
from datetime import datetime, timezone


def test_referral_code_format():
    code1 = ReferralService.generate_referral_code()
    code2 = ReferralService.generate_referral_code()
    assert len(code1) == 8
    assert len(code2) == 8
    assert code1 != code2


@pytest.mark.asyncio
async def test_self_referral_prevention():
    user_repo = AsyncMock()
    referral_repo = AsyncMock()
    xp_service = AsyncMock()

    inviter = User(
        id=1,
        telegram_id=999,
        username="inviter",
        first_name="Inviter",
        xp=0,
        level=1,
        referral_code="REF12345",
        referred_by=None,
        selected_title="Новичок",
        selected_badge="⚡",
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
    user_repo.get_by_referral_code.return_value = inviter

    service = ReferralService(
        referral_repo=referral_repo,
        user_repo=user_repo,
        xp_service=xp_service
    )

    # User 999 tries to use their own code REF12345
    result = await service.process_referral_registration(
        new_user_id=999,
        new_user_name="Same User",
        referral_code="REF12345"
    )
    assert result is None
    referral_repo.add_referral.assert_not_awaited()
    xp_service.award_xp.assert_not_awaited()
