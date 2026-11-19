from app.keyboards.main import (
    get_main_reply_keyboard,
    get_main_inline_keyboard,
    get_back_to_menu_keyboard,
)
from app.keyboards.profile import get_profile_keyboard, get_customization_keyboard
from app.keyboards.inline import (
    get_tasks_menu_keyboard,
    get_task_detail_keyboard,
    get_leaderboard_keyboard,
    get_referral_keyboard,
    get_rewards_keyboard,
    get_admin_panel_keyboard,
    get_admin_task_action_keyboard,
)

__all__ = [
    "get_main_reply_keyboard",
    "get_main_inline_keyboard",
    "get_back_to_menu_keyboard",
    "get_profile_keyboard",
    "get_customization_keyboard",
    "get_tasks_menu_keyboard",
    "get_task_detail_keyboard",
    "get_leaderboard_keyboard",
    "get_referral_keyboard",
    "get_rewards_keyboard",
    "get_admin_panel_keyboard",
    "get_admin_task_action_keyboard",
]
