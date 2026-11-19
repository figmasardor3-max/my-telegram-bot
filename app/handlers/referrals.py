import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from app.database.repositories.users import UserRepository
from app.database.repositories.referrals import ReferralRepository
from app.keyboards.inline import get_referral_keyboard
from app.keyboards.main import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="referrals_handler")


@router.callback_query(F.data == "nav_referrals")
async def handle_nav_referrals(
    callback: CallbackQuery,
    user_repo: UserRepository,
    referral_repo: ReferralRepository,
    bot: Bot
):
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Ошибка: пользователь не найден", show_alert=True)
        return

    ref_count = await referral_repo.get_referrals_count(callback.from_user.id)
    bot_info = await bot.get_me()
    bot_username = bot_info.username or "levelup_bot"

    ref_link = f"https://t.me/{bot_username}?start={user.referral_code}"

    text = (
        f"👥 <b>РЕФЕРАЛЬНАЯ ПРОГРАММА</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Приглашайте друзей в LevelUp и зарабатывайте дополнительный опыт!\n\n"
        f"🎁 <b>Награда за друга:</b> +50 XP сразу после его регистрации\n"
        f"👥 <b>Ваши рефералы:</b> <b>{ref_count}</b> участников\n\n"
        f"🔗 <b>Ваша персональная ссылка:</b>\n"
        f"<code>{ref_link}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Делитесь ссылкой в чатах и социальных сетях!</i>"
    )

    try:
        await callback.message.edit_text(
            text=text,
            reply_markup=get_referral_keyboard(bot_username, user.referral_code),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text=text,
            reply_markup=get_referral_keyboard(bot_username, user.referral_code),
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "referrals_list")
async def handle_referrals_list(
    callback: CallbackQuery,
    referral_repo: ReferralRepository
):
    refs = await referral_repo.get_referrals_list(callback.from_user.id, limit=15)
    if not refs:
        list_str = "<i>У вас пока нет приглашённых участников. Отправьте ссылку друзьям!</i>"
    else:
        lines = []
        for idx, r in enumerate(refs, start=1):
            date_str = r.created_at.strftime("%d.%m.%Y") if hasattr(r.created_at, "strftime") else str(r.created_at)[:10]
            status = "✅ Награда получена (+50 XP)" if r.rewarded else "⏳ В обработке"
            lines.append(f"{idx}. ID: <code>{r.invited_id}</code> ({date_str}) — {status}")
        list_str = "\n".join(lines)

    text = (
        f"👥 <b>СПИСОК ПРИГЛАШЁННЫХ УЧАСТНИКОВ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{list_str}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_back_to_menu_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()
