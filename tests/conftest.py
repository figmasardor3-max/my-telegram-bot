import pytest
from unittest.mock import AsyncMock, MagicMock
from app.database.models import User, Task, Achievement, DailyClaim
from datetime import datetime, timezone


@pytest.fixture
def mock_bot():
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.get_me = AsyncMock(return_value=MagicMock(username="levelup_bot"))
    return bot


@pytest.fixture
def sample_user():
    return User(
        id=1,
        telegram_id=123456789,
        username="testplayer",
        first_name="Test Player",
        xp=150,
        level=2,
        referral_code="TEST1234",
        referred_by=None,
        selected_title="Новичок",
        selected_badge="⚡",
        created_at=datetime.now(timezone.utc),
        last_active_at=datetime.now(timezone.utc),
    )
