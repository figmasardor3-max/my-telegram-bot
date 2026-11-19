from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_profile_keyboard(can_claim_daily: bool = True) -> InlineKeyboardMarkup:
    daily_text = "🎁 Забрать +20 XP" if can_claim_daily else "⏳ Бонус (на перезарядке)"
    daily_action = "claim_daily" if can_claim_daily else "cooldown_info"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=daily_text, callback_data=daily_action)],
            [
                InlineKeyboardButton(text="👥 Пригласить друга", callback_data="nav_referrals"),
                InlineKeyboardButton(text="📜 История XP", callback_data="profile_xp_history"),
            ],
            [
                InlineKeyboardButton(text="✨ Кастомизация", callback_data="profile_customize"),
                InlineKeyboardButton(text="◀️ В главное меню", callback_data="nav_main"),
            ]
        ]
    )


def get_customization_keyboard() -> InlineKeyboardMarkup:
    """Choose title or badge to equip."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ Искра", callback_data="set_badge:⚡"),
                InlineKeyboardButton(text="🔥 Огонь", callback_data="set_badge:🔥"),
                InlineKeyboardButton(text="💎 Алмаз", callback_data="set_badge:💎"),
                InlineKeyboardButton(text="👑 Корона", callback_data="set_badge:👑"),
            ],
            [
                InlineKeyboardButton(text="🔰 Новичок", callback_data="set_title:Новичок"),
                InlineKeyboardButton(text="🧭 Исследователь", callback_data="set_title:Исследователь"),
            ],
            [
                InlineKeyboardButton(text="⚡ Активист", callback_data="set_title:Активист"),
                InlineKeyboardButton(text="👑 Кибер-мастер", callback_data="set_title:Кибер-мастер"),
            ],
            [
                InlineKeyboardButton(text="◀️ Назад в профиль", callback_data="nav_profile")
            ]
        ]
    )
