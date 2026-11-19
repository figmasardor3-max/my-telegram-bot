import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.database.repositories.users import UserRepository
from app.keyboards.inline import get_rewards_keyboard

logger = logging.getLogger(__name__)
router = Router(name="rewards_handler")


REWARDS_CATALOG = [
    {
        "type": "Значок",
        "name": "⚡ Искра (Spark)",
        "condition": "Доступен всем при регистрации",
        "min_level": 1
    },
    {
        "type": "Значок",
        "name": "🔥 Пламя (Flame)",
        "condition": "Достижение 5 уровня или 7 дней ежедневных наград",
        "min_level": 5
    },
    {
        "type": "Значок",
        "name": "💎 Алмаз (Diamond)",
        "condition": "Достижение 10 уровня или 1000 XP",
        "min_level": 10
    },
    {
        "type": "Значок",
        "name": "👑 Корона (Crown)",
        "condition": "Достижение 20 уровня или TOP 3 в рейтинге",
        "min_level": 20
    },
    {
        "type": "Титул",
        "name": "🔰 Новичок",
        "condition": "Начальный статус каждого участника",
        "min_level": 1
    },
    {
        "type": "Титул",
        "name": "🧭 Исследователь",
        "condition": "Достижение 3 уровня",
        "min_level": 3
    },
    {
        "type": "Титул",
        "name": "⚡ Активист",
        "condition": "Достижение 5 уровня",
        "min_level": 5
    },
    {
        "type": "Титул",
        "name": "👑 Кибер-мастер",
        "condition": "Достижение 10 уровня",
        "min_level": 10
    },
]


async def render_rewards_text(user_id: int, user_repo: UserRepository) -> str:
    user = await user_repo.get_by_telegram_id(user_id)
    user_level = user.level if user else 1

    lines = []
    for item in REWARDS_CATALOG:
        is_unlocked = user_level >= item["min_level"]
        status_icon = "🟢" if is_unlocked else "🔒"
        status_str = "Разблокировано" if is_unlocked else f"Требуется LEVEL {item['min_level']}"

        lines.append(
            f"{status_icon} <b>{item['name']}</b> ({item['type']})\n"
            f"    <i>{item['condition']}</i>\n"
            f"    Статус: <b>{status_str}</b>"
        )

    return (
        f"🎁 <b>ВИРТУАЛЬНЫЕ НАГРАДЫ (REWARDS)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"В LevelUp доступны эксклюзивные элементы персонализации: значки и титулы, "
        f"подтверждающие ваш уровень и опыт.\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Вы можете установить любые разблокированные награды в разделе кастомизации.</i>"
    )


@router.message(F.text == "🎁 Награды")
async def handle_rewards_message(message: Message, user_repo: UserRepository):
    text = await render_rewards_text(message.from_user.id, user_repo)
    await message.answer(text=text, reply_markup=get_rewards_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "nav_rewards")
async def handle_nav_rewards(callback: CallbackQuery, user_repo: UserRepository):
    text = await render_rewards_text(callback.from_user.id, user_repo)
    try:
        await callback.message.edit_text(text=text, reply_markup=get_rewards_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text=text, reply_markup=get_rewards_keyboard(), parse_mode="HTML")
    await callback.answer()
