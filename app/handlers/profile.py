import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from app.database.repositories.users import UserRepository
from app.database.repositories.xp import XPRepository
from app.services.levels import LevelService
from app.services.daily import DailyService
from app.keyboards.profile import get_profile_keyboard, get_customization_keyboard
from app.keyboards.main import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="profile_handler")


async def render_profile_text(stats: dict, daily_status: dict) -> str:
    user = stats["user"]
    rank = stats["rank"]
    completed_tasks = stats["completed_tasks"]
    achievements_count = stats["achievements_count"]
    referrals_count = stats["referrals_count"]

    curr_in_lvl, total_in_lvl, pct = LevelService.get_level_progress(user.xp)
    progress_bar = LevelService.render_progress_bar(curr_in_lvl, total_in_lvl)

    badge = user.selected_badge or "⚡"
    title = user.selected_title or "Новичок"
    name = user.first_name

    daily_indicator = "🟢 Доступен" if daily_status["can_claim"] else f"⏳ Через {daily_status['time_left_str']}"

    return (
        f"👤 <b>USER PROFILE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{badge} <b>{name}</b>  |  <i>{title}</i>\n\n"
        f"🏆 <b>LEVEL {user.level:02d}</b>\n"
        f"⚡ Опыт: <b>{curr_in_lvl} / {total_in_lvl} XP</b>\n"
        f"Прогресс: <code>[{progress_bar}]</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>СТАТИСТИКА:</b>\n"
        f"• Всего XP: <b>{user.xp}</b>\n"
        f"• Место в рейтинге: <b>#{rank}</b>\n"
        f"• Заданий выполнено: <b>{completed_tasks}</b>\n"
        f"• Достижений открыто: <b>{achievements_count}</b>\n"
        f"• Приглашено друзей: <b>{referrals_count}</b>\n"
        f"• Ежедневный бонус: <b>{daily_indicator}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>YOUR PROGRESS STARTS HERE</i>"
    )


@router.message(F.text == "👤 Профиль")
async def handle_profile_message(
    message: Message,
    user_repo: UserRepository,
    daily_service: DailyService
):
    stats = await user_repo.get_user_stats(message.from_user.id)
    if not stats:
        await message.answer("Пользователь не найден. Введите /start.")
        return

    daily_status = await daily_service.get_daily_status(message.from_user.id)
    text = await render_profile_text(stats, daily_status)

    await message.answer(
        text=text,
        reply_markup=get_profile_keyboard(can_claim_daily=daily_status["can_claim"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "nav_profile")
async def handle_nav_profile_callback(
    callback: CallbackQuery,
    user_repo: UserRepository,
    daily_service: DailyService
):
    stats = await user_repo.get_user_stats(callback.from_user.id)
    if not stats:
        await callback.answer("Ошибка загрузки профиля", show_alert=True)
        return

    daily_status = await daily_service.get_daily_status(callback.from_user.id)
    text = await render_profile_text(stats, daily_status)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_profile_keyboard(can_claim_daily=daily_status["can_claim"]),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text=text,
            reply_markup=get_profile_keyboard(can_claim_daily=daily_status["can_claim"]),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "claim_daily")
async def handle_claim_daily(
    callback: CallbackQuery,
    user_repo: UserRepository,
    daily_service: DailyService,
    bot: Bot
):
    success, msg, _ = await daily_service.claim_daily_reward(callback.from_user.id, bot)
    await callback.answer(msg.split("\n")[0] if success else msg, show_alert=True)

    # Refresh profile card
    stats = await user_repo.get_user_stats(callback.from_user.id)
    daily_status = await daily_service.get_daily_status(callback.from_user.id)
    text = await render_profile_text(stats, daily_status)

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_profile_keyboard(can_claim_daily=daily_status["can_claim"]),
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data == "cooldown_info")
async def handle_cooldown_info(callback: CallbackQuery, daily_service: DailyService):
    daily_status = await daily_service.get_daily_status(callback.from_user.id)
    await callback.answer(
        f"⏳ Награда уже получена! Следующая доступна через {daily_status['time_left_str']} (в 00:00 UTC).",
        show_alert=True
    )


@router.callback_query(F.data == "profile_customize")
async def handle_profile_customize(callback: CallbackQuery):
    text = (
        "✨ <b>КАСТОМИЗАЦИЯ ПРОФИЛЯ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Выберите значок или титул для отображения в вашем профиле:\n\n"
        "<i>Значки и титулы подчеркивают ваш статус и достижения в LevelUp.</i>"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=get_customization_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_badge:"))
async def handle_set_badge(callback: CallbackQuery, user_repo: UserRepository):
    badge = callback.data.split(":", 1)[1]
    await user_repo.update_customization(callback.from_user.id, badge=badge)
    await callback.answer(f"Значок {badge} установлен!", show_alert=False)

    # Return to profile
    stats = await user_repo.get_user_stats(callback.from_user.id)
    from app.services.daily import DailyService
    daily_status = {"can_claim": False, "time_left_str": ""}
    text = await render_profile_text(stats, daily_status)
    await callback.message.edit_text(
        text=text,
        reply_markup=get_profile_keyboard(can_claim_daily=False),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("set_title:"))
async def handle_set_title(callback: CallbackQuery, user_repo: UserRepository):
    title = callback.data.split(":", 1)[1]
    await user_repo.update_customization(callback.from_user.id, title=title)
    await callback.answer(f"Титул «{title}» установлен!", show_alert=False)

    # Return to profile
    stats = await user_repo.get_user_stats(callback.from_user.id)
    daily_status = {"can_claim": False, "time_left_str": ""}
    text = await render_profile_text(stats, daily_status)
    await callback.message.edit_text(
        text=text,
        reply_markup=get_profile_keyboard(can_claim_daily=False),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "profile_xp_history")
async def handle_profile_xp_history(
    callback: CallbackQuery,
    xp_repo: XPRepository
):
    history = await xp_repo.get_history(callback.from_user.id, limit=7)
    if not history:
        history_text = "<i>История начислений пуста. Выполняйте задания!</i>"
    else:
        lines = []
        for event in history:
            sign = "+" if event.amount > 0 else ""
            created = event.created_at
            time_str = created.strftime('%d.%m %H:%M') if hasattr(created, 'strftime') else str(created)[:16]
            lines.append(
                f"• <b>{sign}{event.amount} XP</b> — {event.reason} "
                f"(<code>{time_str}</code>)"
            )
        history_text = "\n".join(lines)

    text = (
        "📜 <b>ИСТОРИЯ НАЧИСЛЕНИЙ XP</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{history_text}\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
