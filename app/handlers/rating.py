import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.database.repositories.xp import XPRepository
from app.database.repositories.users import UserRepository
from app.keyboards.inline import get_leaderboard_keyboard

logger = logging.getLogger(__name__)
router = Router(name="rating_handler")


async def render_leaderboard_text(
    user_id: int,
    tab: str,
    xp_repo: XPRepository,
    user_repo: UserRepository
) -> str:
    if tab == "weekly":
        title = "📅 WEEKLY TOP (ПОСЛЕДНИЕ 7 ДНЕЙ)"
        entries = await xp_repo.get_period_leaderboard(days=7, limit=10)
        user_rank, user_score = await xp_repo.get_user_period_stats(user_id, days=7)
    elif tab == "monthly":
        title = "📆 MONTHLY TOP (ПОСЛЕДНИЕ 30 ДНЕЙ)"
        entries = await xp_repo.get_period_leaderboard(days=30, limit=10)
        user_rank, user_score = await xp_repo.get_user_period_stats(user_id, days=30)
    else:
        title = "🌍 GLOBAL TOP (ВСЕ ВРЕМЯ)"
        entries = await xp_repo.get_global_leaderboard(limit=10)
        user_rank = await user_repo.get_user_rank(user_id)
        user = await user_repo.get_by_telegram_id(user_id)
        user_score = user.xp if user else 0

    lines = []
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}

    for e in entries:
        rank_icon = medals.get(e.rank, f"<b>#{e.rank:02d}</b>")
        badge = e.selected_badge or "⚡"
        username_str = f"@{e.username}" if e.username else e.first_name
        is_current_user = " 👈 <i>(Вы)</i>" if e.telegram_id == user_id else ""

        lines.append(
            f"{rank_icon} {badge} <b>{username_str}</b> — LVL {e.level} | <b>{e.xp} XP</b>{is_current_user}"
        )

    if not entries:
        board_content = "<i>В этом периоде пока нет активности. Будьте первым!</i>"
    else:
        board_content = "\n".join(lines)

    return (
        f"🏆 <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{board_content}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>ВАША ПОЗИЦИЯ:</b>\n"
        f"Место: <b>#{user_rank}</b>  |  Очки периода: <b>{user_score} XP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Рейтинг обновляется в реальном времени.</i>"
    )


@router.message(F.text == "🏆 Рейтинг")
async def handle_rating_message(
    message: Message,
    xp_repo: XPRepository,
    user_repo: UserRepository
):
    text = await render_leaderboard_text(message.from_user.id, "global", xp_repo, user_repo)
    await message.answer(
        text=text,
        reply_markup=get_leaderboard_keyboard(active_tab="global"),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "nav_rating")
async def handle_nav_rating(
    callback: CallbackQuery,
    xp_repo: XPRepository,
    user_repo: UserRepository
):
    text = await render_leaderboard_text(callback.from_user.id, "global", xp_repo, user_repo)
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_leaderboard_keyboard(active_tab="global"),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text=text,
            reply_markup=get_leaderboard_keyboard(active_tab="global"),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("rating_tab:"))
async def handle_rating_tab(
    callback: CallbackQuery,
    xp_repo: XPRepository,
    user_repo: UserRepository
):
    tab = callback.data.split(":", 1)[1]
    text = await render_leaderboard_text(callback.from_user.id, tab, xp_repo, user_repo)
    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_leaderboard_keyboard(active_tab=tab),
            parse_mode="HTML"
        )
    except Exception:
        pass
    await callback.answer()
