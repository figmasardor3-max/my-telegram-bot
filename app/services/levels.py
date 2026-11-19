from typing import Tuple


class LevelService:
    XP_PER_LEVEL: int = 100

    @staticmethod
    def calculate_level(xp: int) -> int:
        """
        Calculates level based on XP.
        Base level is 1. Every 100 XP adds 1 level.
        Level 1: 0 - 99 XP
        Level 2: 100 - 199 XP
        Level 3: 200 - 299 XP, etc.
        """
        safe_xp = max(0, xp)
        return (safe_xp // LevelService.XP_PER_LEVEL) + 1

    @staticmethod
    def get_level_progress(xp: int) -> Tuple[int, int, float]:
        """
        Returns (current_xp_in_level, needed_for_next_level, percentage)
        """
        safe_xp = max(0, xp)
        current_in_level = safe_xp % LevelService.XP_PER_LEVEL
        total_in_level = LevelService.XP_PER_LEVEL
        pct = (current_in_level / total_in_level) * 100.0
        return current_in_level, total_in_level, pct

    @staticmethod
    def render_progress_bar(current: int, total: int = 100, length: int = 10) -> str:
        """
        Renders a minimalist high-tech progress bar:
        E.g. [▰▰▰▰▱▱▱▱▱▱] 40%
        """
        if total <= 0:
            return "▱" * length + " 0%"
        ratio = min(1.0, max(0.0, current / total))
        filled_count = int(round(ratio * length))
        empty_count = length - filled_count
        pct = int(round(ratio * 100))
        return f"{'▰' * filled_count}{'▱' * empty_count} {pct}%"
