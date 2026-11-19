import logging
from datetime import datetime, date
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.database.repositories.achievements import AchievementRepository
from app.keyboards.main import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="achievements_handler")


def format_dt(val, fmt="%d.%m.%Y") -> str:
    if isinstance(val, (datetime, date)):
        return val.strftime(fmt)
    if isinstance(val, str):
        try:
            d = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return d.strftime(fmt)
        except Exception:
            return val[:10]
    return str(val)


async def render_achievements_text(user_id: int, ach_repo: AchievementRepository) -> str:
    all_achievements = await ach_repo.list_all()
    unlocked_details = await ach_repo.get_user_achievements_with_details(user_id)
    unlocked_dict = {ach.id: dt for ach, dt in unlocked_details}

    unlocked_count = len(unlocked_dict)
    total_count = len(all_achievements)
    pct = int(round((unlocked_count / total_count * 100))) if total_count > 0 else 0

    lines = []
    for a in all_achievements:
        if a.id in unlocked_dict:
            unlocked_at = unlocked_dict[a.id]
            date_str = format_dt(unlocked_at, "%d.%m.%Y")
            lines.append(
                f"✅ {a.icon} <b>{a.title}</b> (+{a.reward_xp} XP)\n"
                f"    <i>{a.description}</i>\n"
                f"    🔓 Разблокировано: <code>{date_str}</code>"
            )
        else:
            lines.append(
                f"🔒 {a.icon} <b>{a.title}</b> (+{a.reward_xp} XP)\n"
                f"    <i>{a.description}</i>"
            )

    return (
        f"🎖 <b>ДОСТИЖЕНИЯ (ACHIEVEMENTS)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Прогресс: <b>{unlocked_count} / {total_count}</b> ({pct}%)\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        + "\n\n".join(lines)
        + "\n\n━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Выполняйте задания, проявляйте активность и открывайте все награды!</i>"
    )


@router.message(F.text == "🎖 Достижения")
async def handle_achievements_message(message: Message, achievement_repo: AchievementRepository):
    text = await render_achievements_text(message.from_user.id, achievement_repo)
    await message.answer(text=text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "nav_achievements")
async def handle_nav_achievements(callback: CallbackQuery, achievement_repo: AchievementRepository):
    text = await render_achievements_text(callback.from_user.id, achievement_repo)
    try:
        await callback.message.edit_text(text=text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text=text, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
