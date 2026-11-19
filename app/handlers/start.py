import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
from app.config import settings
from app.database.repositories.users import UserRepository
from app.services.referrals import ReferralService
from app.services.achievements import AchievementService
from app.keyboards.main import get_main_reply_keyboard, get_main_inline_keyboard

logger = logging.getLogger(__name__)
router = Router(name="start_handler")


WELCOME_TEXT = (
    "⚡ <b>LEVELUP — YOUR PROGRESS STARTS HERE</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "Добро пожаловать в экосистему геймификации <b>LevelUp</b>.\n\n"
    "Развивайтесь внутри платформы, зарабатывайте <b>XP</b>, открывайте новые уровни, "
    "выполняйте ежедневные задания и соревнуйтесь за лидерство в рейтинге.\n\n"
    "🔹 <b>Каждые 100 XP</b> повышают ваш уровень\n"
    "🔹 <b>Ежедневный бонус</b> +20 XP каждый день\n"
    "🔹 <b>Задания и награды</b> для активных участников\n"
    "🔹 <b>Реферальная система</b> +50 XP за приглашённого друга\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "Выберите раздел для продолжения:"
)


@router.message(CommandStart())
async def handle_start(
    message: Message,
    command: CommandObject,
    user_repo: UserRepository,
    referral_service: ReferralService,
    achievement_service: AchievementService,
    bot: Bot
):
    tg_user = message.from_user
    if not tg_user:
        return

    existing_user = await user_repo.get_by_telegram_id(tg_user.id)
    is_new = existing_user is None

    # Handle referral code if passed: /start <referral_code>
    ref_arg = command.args.strip() if command.args else None
    inviter_id = None

    if is_new:
        ref_code = ReferralService.generate_referral_code()
        if ref_arg:
            inviter_id = await referral_service.process_referral_registration(
                new_user_id=tg_user.id,
                new_user_name=tg_user.first_name,
                referral_code=ref_arg,
                bot=bot
            )

        user = await user_repo.create_user(
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
            referral_code=ref_code,
            referred_by=inviter_id
        )
        logger.info(f"New user registered: {tg_user.id} (@{tg_user.username})")

        # Unlock First Step achievement
        await achievement_service.check_registration(tg_user.id, bot)
    else:
        user = existing_user

    is_admin = tg_user.id in settings.ADMIN_IDS

    # Send persistent reply keyboard first
    await message.answer(
        text="🎮 <i>Главное меню активировано</i>",
        reply_markup=get_main_reply_keyboard(),
        parse_mode="HTML"
    )

    # Send main interactive card
    await message.answer(
        text=WELCOME_TEXT,
        reply_markup=get_main_inline_keyboard(is_admin=is_admin),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "nav_main")
async def handle_nav_main(callback: CallbackQuery):
    is_admin = callback.from_user.id in settings.ADMIN_IDS
    try:
        await callback.message.edit_text(
            text=WELCOME_TEXT,
            reply_markup=get_main_inline_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )
    except Exception:
        await callback.message.answer(
            text=WELCOME_TEXT,
            reply_markup=get_main_inline_keyboard(is_admin=is_admin),
            parse_mode="HTML"
        )
    await callback.answer()
