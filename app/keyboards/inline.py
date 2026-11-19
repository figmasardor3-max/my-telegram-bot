from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models import Task


def get_tasks_menu_keyboard(category: str, tasks_data: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """List of tasks with status icons and category tabs."""
    keyboard: List[List[InlineKeyboardButton]] = []

    # Category tabs
    daily_btn_text = "⚡ DAILY [✓]" if category == "daily" else "DAILY"
    weekly_btn_text = "🔥 WEEKLY [✓]" if category == "weekly" else "WEEKLY"

    keyboard.append([
        InlineKeyboardButton(text=daily_btn_text, callback_data="tasks_cat:daily"),
        InlineKeyboardButton(text=weekly_btn_text, callback_data="tasks_cat:weekly"),
    ])

    # Task rows
    for item in tasks_data:
        task: Task = item["task"]
        is_done: bool = item["is_completed"]
        status_icon = "✅" if is_done else "⚡"
        btn_text = f"{status_icon} {task.title} (+{task.reward_xp} XP)"
        keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data=f"task_view:{task.id}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_task_detail_keyboard(task_id: int, is_completed: bool, category: str) -> InlineKeyboardMarkup:
    buttons = []
    if not is_completed:
        buttons.append([InlineKeyboardButton(text="✅ Проверить и забрать награду", callback_data=f"task_claim:{task_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ К списку заданий", callback_data=f"tasks_cat:{category}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_leaderboard_keyboard(active_tab: str = "global") -> InlineKeyboardMarkup:
    global_text = "🌍 GLOBAL [✓]" if active_tab == "global" else "🌍 GLOBAL"
    weekly_text = "📅 WEEKLY [✓]" if active_tab == "weekly" else "📅 WEEKLY"
    monthly_text = "📆 MONTHLY [✓]" if active_tab == "monthly" else "📆 MONTHLY"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=global_text, callback_data="rating_tab:global"),
                InlineKeyboardButton(text=weekly_text, callback_data="rating_tab:weekly"),
                InlineKeyboardButton(text=monthly_text, callback_data="rating_tab:monthly"),
            ],
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data=f"rating_tab:{active_tab}"),
                InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main"),
            ]
        ]
    )


def get_referral_keyboard(bot_username: str, ref_code: str) -> InlineKeyboardMarkup:
    invite_url = f"https://t.me/{bot_username}?start={ref_code}"
    share_url = f"https://t.me/share/url?url={invite_url}&text=Вступай%20в%20LevelUp%20и%20прокачивай%20свой%20уровень!"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Поделиться ссылкой", url=share_url)],
            [
                InlineKeyboardButton(text="👥 Список рефералов", callback_data="referrals_list"),
                InlineKeyboardButton(text="◀️ В профиль", callback_data="nav_profile"),
            ]
        ]
    )


def get_rewards_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎨 Перейти к кастомизации", callback_data="profile_customize")
            ],
            [
                InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main")
            ]
        ]
    )


def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton(text="🔍 Поиск игрока", callback_data="admin_search_user"),
            ],
            [
                InlineKeyboardButton(text="🎯 Создать задание", callback_data="admin_create_task"),
                InlineKeyboardButton(text="📋 Список заданий", callback_data="admin_list_tasks"),
            ],
            [
                InlineKeyboardButton(text="⚡ Начислить/Снять XP", callback_data="admin_adjust_xp"),
                InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
            ],
            [
                InlineKeyboardButton(text="📜 Аудит XP", callback_data="admin_xp_audit"),
                InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main"),
            ]
        ]
    )


def get_admin_task_action_keyboard(task_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Деактивировать" if is_active else "🟢 Активировать"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_text, callback_data=f"adm_toggle_task:{task_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"adm_del_task:{task_id}"),
            ],
            [
                InlineKeyboardButton(text="◀️ К списку заданий", callback_data="admin_list_tasks")
            ]
        ]
    )
