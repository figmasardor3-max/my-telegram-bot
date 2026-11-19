import pytest
from datetime import datetime, timezone
from app.database.connection import init_pool, close_pool
from app.database.migrations import apply_migrations
from app.database.repositories import (
    UserRepository,
    XPRepository,
    DailyRepository,
    TaskRepository,
    AchievementRepository,
    ReferralRepository
)


@pytest.mark.asyncio
async def test_full_database_lifecycle():
    # 1. Init pool with in-memory SQLite for test
    pool = await init_pool("sqlite:///:memory:")
    await apply_migrations(pool)

    user_repo = UserRepository(pool)
    xp_repo = XPRepository(pool)
    daily_repo = DailyRepository(pool)
    task_repo = TaskRepository(pool)
    achievement_repo = AchievementRepository(pool)
    referral_repo = ReferralRepository(pool)

    # 2. Test User Creation
    u1 = await user_repo.create_user(
        telegram_id=111,
        username="player1",
        first_name="Player One",
        referral_code="REF111"
    )
    assert u1.telegram_id == 111
    assert u1.xp == 0
    assert u1.level == 1

    # 3. Test XP award with transaction & level up
    awarded, new_xp, new_lvl, lvl_up = await xp_repo.add_xp_with_transaction(
        user_id=111,
        amount=150,
        reason="Initial bonus",
        idempotency_key="idemp_111_init"
    )
    assert awarded is True
    assert new_xp == 150
    assert new_lvl == 2
    assert lvl_up is True

    # Duplicate idempotency check
    awarded_dup, _, _, _ = await xp_repo.add_xp_with_transaction(
        user_id=111,
        amount=150,
        reason="Initial bonus",
        idempotency_key="idemp_111_init"
    )
    assert awarded_dup is False

    # 4. Test User 2 & Referrals
    u2 = await user_repo.create_user(
        telegram_id=222,
        username="player2",
        first_name="Player Two",
        referral_code="REF222",
        referred_by=111
    )
    ref_added = await referral_repo.add_referral(inviter_id=111, invited_id=222)
    assert ref_added is True
    ref_count = await referral_repo.get_referrals_count(111)
    assert ref_count == 1

    # 5. Test Daily Claim
    claim_success = await daily_repo.record_claim(111, 20)
    assert claim_success is True
    # Duplicate claim on same day fails
    claim_dup = await daily_repo.record_claim(111, 20)
    assert claim_dup is False

    # 6. Test Tasks
    tasks = await task_repo.list_active_tasks()
    assert len(tasks) > 0
    first_task = tasks[0]

    mark_task = await task_repo.mark_completed(111, first_task.id)
    assert mark_task is True
    completed_ids = await task_repo.get_completed_task_ids(111)
    assert first_task.id in completed_ids

    # 7. Test Achievements
    achievements = await achievement_repo.list_all()
    assert len(achievements) > 0
    first_ach = achievements[0]
    unlocked = await achievement_repo.unlock(111, first_ach.id)
    assert unlocked is True
    unlocked_ids = await achievement_repo.get_user_unlocked_ids(111)
    assert first_ach.id in unlocked_ids

    # 8. Test Leaderboard
    leaderboard = await xp_repo.get_global_leaderboard(10)
    assert len(leaderboard) >= 2
    assert leaderboard[0].telegram_id == 111

    # 9. Test User Stats
    stats = await user_repo.get_user_stats(111)
    assert stats["rank"] == 1
    assert stats["completed_tasks"] == 1
    assert stats["achievements_count"] == 1
    assert stats["referrals_count"] == 1

    await close_pool()
