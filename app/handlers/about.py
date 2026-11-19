import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from app.keyboards.main import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="about_handler")

ABOUT_TEXT = (
    "ℹ️ <b>О ПРОЕКТЕ LEVELUP</b>\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "<b>Слоган:</b> <i>YOUR PROGRESS STARTS HERE</i>\n\n"
    "<b>LevelUp</b> — это современная геймификационная платформа в Telegram, "
    "построенная на прозрачной системе опыта (XP), уровней и рейтингов.\n\n"
    "⚙️ <b>КАК ЭТО РАБОТАЕТ:</b>\n"
    "• <b>Уровни:</b> каждый уровень требует 100 XP. Достигайте новых вершин!\n"
    "• <b>Daily Bonus:</b> заходите каждый день и получайте +20 XP.\n"
    "• <b>Задания:</b> выполняйте регулярные квесты и получайте солидные награды.\n"
    "• <b>Рейтинг:</b> соревнуйтесь с другими игроками в глобальном, недельном и месячном топах.\n"
    "• <b>Рефералы:</b> делитесь ссылкой и получайте +50 XP за каждого друга.\n"
    "• <b>Награды:</b> открывайте титулы и значки без платных механик или азартных игр.\n\n"
    "🛡 <b>ЧЕСТНАЯ ИГРА:</b>\n"
    "Все начисления строго защищены от накруток и дубликатов с помощью транзакций "
    "и ключей идемпотентности.\n"
    "━━━━━━━━━━━━━━━━━━━\n"
    "<i>Версия: 1.0.0 Production</i>"
)


@router.message(F.text == "ℹ️ О проекте")
async def handle_about_message(message: Message):
    await message.answer(text=ABOUT_TEXT, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "nav_about")
async def handle_nav_about(callback: CallbackQuery):
    try:
        await callback.message.edit_text(text=ABOUT_TEXT, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text=ABOUT_TEXT, reply_markup=get_back_to_menu_keyboard(), parse_mode="HTML")
    await callback.answer()
