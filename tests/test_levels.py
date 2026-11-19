import pytest
from app.services.levels import LevelService


def test_calculate_level():
    assert LevelService.calculate_level(0) == 1
    assert LevelService.calculate_level(50) == 1
    assert LevelService.calculate_level(99) == 1
    assert LevelService.calculate_level(100) == 2
    assert LevelService.calculate_level(150) == 2
    assert LevelService.calculate_level(199) == 2
    assert LevelService.calculate_level(200) == 3
    assert LevelService.calculate_level(1000) == 11
    # Negative XP safety check
    assert LevelService.calculate_level(-50) == 1


def test_level_progress():
    curr, total, pct = LevelService.get_level_progress(0)
    assert curr == 0
    assert total == 100
    assert pct == 0.0

    curr, total, pct = LevelService.get_level_progress(45)
    assert curr == 45
    assert total == 100
    assert pct == 45.0

    curr, total, pct = LevelService.get_level_progress(145)
    assert curr == 45
    assert total == 100
    assert pct == 45.0


def test_render_progress_bar():
    bar_0 = LevelService.render_progress_bar(0, 100, length=10)
    assert bar_0 == "▱▱▱▱▱▱▱▱▱▱ 0%"

    bar_50 = LevelService.render_progress_bar(50, 100, length=10)
    assert bar_50 == "▰▰▰▰▰▱▱▱▱▱ 50%"

    bar_100 = LevelService.render_progress_bar(100, 100, length=10)
    assert bar_100 == "▰▰▰▰▰▰▰▰▰▰ 100%"
