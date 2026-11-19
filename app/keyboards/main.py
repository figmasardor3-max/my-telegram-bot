from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Main persistent bottom keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🎯 Задания")],
            [KeyboardButton(text="🏆 Рейтинг"), KeyboardButton(text="🎖 Достижения")],
            [KeyboardButton(text="🎁 Награды"), KeyboardButton(text="ℹ️ О проекте")]
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def get_main_inline_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    rows = [
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="nav_profile"),
            InlineKeyboardButton(text="🎯 Задания", callback_data="nav_tasks"),
        ],
        [
            InlineKeyboardButton(text="🏆 Рейтинг", callback_data="nav_rating"),
            InlineKeyboardButton(text="🎖 Достижения", callback_data="nav_achievements"),
        ],
        [
            InlineKeyboardButton(text="🎁 Награды", callback_data="nav_rewards"),
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="nav_about"),
        ]
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="🛡 Админ-панель", callback_data="admin_panel")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Standard back button to main menu."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main")]
        ]
    )
