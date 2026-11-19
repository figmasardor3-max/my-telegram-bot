import logging
import asyncio
from typing import Optional
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import settings
from app.database.repositories.users import UserRepository
from app.database.repositories.xp import XPRepository
from app.database.repositories.tasks import TaskRepository
from app.services.xp import XPService
from app.keyboards.inline import (
    get_admin_panel_keyboard,
    get_admin_task_action_keyboard,
)
from app.keyboards.main import get_back_to_menu_keyboard

logger = logging.getLogger(__name__)
router = Router(name="admin_handler")


class AdminStates(StatesGroup):
    waiting_for_search_id = State()
    waiting_for_xp_user_id = State()
    waiting_for_xp_amount = State()
    waiting_for_xp_reason = State()
    waiting_for_task_title = State()
    waiting_for_task_desc = State()
    waiting_for_task_cat = State()
    waiting_for_task_reward = State()
    waiting_for_broadcast_msg = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


@router.message(Command("admin"))
async def handle_admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ <b>Доступ запрещен.</b> У вас нет прав администратора.", parse_mode="HTML")
        return

    text = (
        "🛡 <b>ПАНЕЛЬ УПРАВЛЕНИЯ LEVELUP (ADMIN)</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в административный интерфейс бота.\n"
        "Выберите раздел для мониторинга и управления системой:"
    )
    await message.answer(text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin_panel")
async def handle_admin_panel_callback(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    text = (
        "🛡 <b>ПАНЕЛЬ УПРАВЛЕНИЯ LEVELUP (ADMIN)</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Добро пожаловать в административный интерфейс бота.\n"
        "Выберите раздел для мониторинга и управления системой:"
    )
    await callback.message.edit_text(text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(
    callback: CallbackQuery,
    user_repo: UserRepository,
    xp_repo: XPRepository
):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    total_users = await user_repo.get_total_users_count()
    new_today = await user_repo.get_new_users_today_count()
    active_week = await user_repo.get_active_users_week_count()
    total_xp = await xp_repo.get_total_xp_distributed()

    text = (
        "📊 <b>СИСТЕМНАЯ СТАТИСТИКА LEVELUP</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"• Всего пользователей: <b>{total_users}</b>\n"
        f"• Новых за сегодня: <b>{new_today}</b>\n"
        f"• Активных за 7 дней: <b>{active_week}</b>\n"
        f"• Всего начислено XP: <b>{total_xp:,} XP</b>\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")]]
    )
    await callback.message.edit_text(text=text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()


# ---------------- USER SEARCH ----------------
@router.callback_query(F.data == "admin_search_user")
async def handle_admin_search_prompt(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_search_id)
    await callback.message.edit_text(
        "🔍 <b>ПОИСК ПОЛЬЗОВАТЕЛЯ</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Введите числовой <b>Telegram ID</b> пользователя для проверки:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")]]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_search_id)
async def handle_admin_search_id(message: Message, state: FSMContext, user_repo: UserRepository):
    if not is_admin(message.from_user.id):
        return

    txt = message.text.strip()
    if not txt.isdigit():
        await message.answer("⚠️ Пожалуйста, введите корректный числовой Telegram ID:")
        return

    target_id = int(txt)
    stats = await user_repo.get_user_stats(target_id)
    await state.clear()

    if not stats:
        await message.answer(
            f"❌ Пользователь с ID <code>{target_id}</code> не найден в базе данных.",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode="HTML"
        )
        return

    u = stats["user"]
    created_str = u.created_at.strftime('%d.%m.%Y %H:%M') if hasattr(u.created_at, 'strftime') else str(u.created_at)[:16]
    active_str = u.last_active_at.strftime('%d.%m.%Y %H:%M') if hasattr(u.last_active_at, 'strftime') else str(u.last_active_at)[:16]
    text = (
        f"👤 <b>ДАННЫЕ ПОЛЬЗОВАТЕЛЯ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"• ID: <code>{u.telegram_id}</code>\n"
        f"• Имя: <b>{u.first_name}</b>\n"
        f"• Username: @{u.username or 'нет'}\n"
        f"• Уровень: <b>LEVEL {u.level}</b>\n"
        f"• XP: <b>{u.xp}</b>\n"
        f"• Реферальный код: <code>{u.referral_code}</code>\n"
        f"• Приглашён пользователем: <code>{u.referred_by or 'нет'}</code>\n"
        f"• Выполнено заданий: <b>{stats['completed_tasks']}</b>\n"
        f"• Достижений: <b>{stats['achievements_count']}</b>\n"
        f"• Рефералов: <b>{stats['referrals_count']}</b>\n"
        f"• Зарегистрирован: <code>{created_str}</code>\n"
        f"• Последняя активность: <code>{active_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(text=text, reply_markup=get_admin_panel_keyboard(), parse_mode="HTML")


# ---------------- ADJUST XP ----------------
@router.callback_query(F.data == "admin_adjust_xp")
async def handle_admin_adjust_xp_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_for_xp_user_id)
    await callback.message.edit_text(
        "⚡ <b>ИЗМЕНЕНИЕ ОПЫТА (XP)</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Шаг 1/3: Введите <b>Telegram ID</b> целевого пользователя:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")]]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_xp_user_id)
async def handle_adjust_xp_user(message: Message, state: FSMContext, user_repo: UserRepository):
    if not is_admin(message.from_user.id):
        return

    if not message.text.strip().isdigit():
        await message.answer("⚠️ Введите числовой Telegram ID:")
        return

    target_id = int(message.text.strip())
    user = await user_repo.get_by_telegram_id(target_id)
    if not user:
        await message.answer(f"❌ Пользователь {target_id} не найден. Попробуйте снова:")
        return

    await state.update_data(target_id=target_id)
    await state.set_state(AdminStates.waiting_for_xp_amount)
    await message.answer(
        f"Пользователь найден: <b>{user.first_name}</b> (Текущий XP: {user.xp})\n\n"
        f"Шаг 2/3: Введите количество XP (положительное число для начисления или отрицательное со знаком минус для списания, например <code>100</code> или <code>-50</code>):",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_xp_amount)
async def handle_adjust_xp_amount(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    raw = message.text.strip()
    try:
        amount = int(raw)
        if amount == 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Введите ненулевое целое число (например, 100 или -50):")
        return

    await state.update_data(amount=amount)
    await state.set_state(AdminStates.waiting_for_xp_reason)
    await message.answer(
        "Шаг 3/3: Введите <b>обязательную причину</b> операции для записи в аудит-лог:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_xp_reason)
async def handle_adjust_xp_reason(
    message: Message,
    state: FSMContext,
    xp_service: XPService,
    bot: Bot
):
    if not is_admin(message.from_user.id):
        return

    reason = message.text.strip()
    if len(reason) < 3:
        await message.answer("⚠️ Причина должна содержать не менее 3 символов:")
        return

    data = await state.get_data()
    target_id = data["target_id"]
    amount = data["amount"]
    await state.clear()

    if amount > 0:
        success, new_xp, new_lvl, lvl_up = await xp_service.award_xp(
            user_id=target_id,
            amount=amount,
            reason=f"[ADMIN BONUS] {reason}",
            bot=bot
        )
    else:
        success, new_xp, new_lvl = await xp_service.deduct_xp(
            user_id=target_id,
            amount=abs(amount),
            reason=reason,
            bot=bot
        )

    await message.answer(
        f"✅ <b>ОПЕРАЦИЯ ВЫПОЛНЕНА!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Пользователь: <code>{target_id}</code>\n"
        f"Изменение: <b>{amount:+d} XP</b>\n"
        f"Новый баланс: <b>{new_xp} XP</b> (LEVEL {new_lvl})\n"
        f"Причина: <i>{reason}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


# ---------------- TASK MANAGEMENT ----------------
@router.callback_query(F.data == "admin_list_tasks")
async def handle_admin_list_tasks(callback: CallbackQuery, task_repo: TaskRepository):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    tasks = await task_repo.get_all_tasks_admin()
    if not tasks:
        await callback.message.edit_text(
            "📋 Список заданий пуст.",
            reply_markup=get_admin_panel_keyboard()
        )
        await callback.answer()
        return

    keyboard = []
    for t in tasks:
        status_icon = "🟢" if t.is_active else "🔴"
        btn_text = f"{status_icon} [{t.category.upper()}] {t.title} (+{t.reward_xp} XP)"
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"adm_task_detail:{t.id}")])

    keyboard.append([InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")])

    await callback.message.edit_text(
        "📋 <b>УПРАВЛЕНИЕ ЗАДАНИЯМИ</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Нажмите на задание для управления статусом или удаления:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_task_detail:"))
async def handle_admin_task_detail(callback: CallbackQuery, task_repo: TaskRepository):
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split(":", 1)[1])
    task = await task_repo.get_by_id(task_id)
    if not task:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    status_str = "🟢 Активно" if task.is_active else "🔴 Отключено"
    text = (
        f"🎯 <b>ЗАДАНИЕ #{task.id}: {task.title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Категория: <b>{task.category}</b>\n"
        f"Награда: <b>+{task.reward_xp} XP</b>\n"
        f"Тип условия: <code>{task.condition_type}</code> (цель: {task.condition_target})\n"
        f"Статус: <b>{status_str}</b>\n\n"
        f"Описание:\n<i>{task.description}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=get_admin_task_action_keyboard(task.id, task.is_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm_toggle_task:"))
async def handle_admin_toggle_task(callback: CallbackQuery, task_repo: TaskRepository):
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split(":", 1)[1])
    new_state = await task_repo.toggle_active(task_id)
    state_str = "активировано" if new_state else "деактивировано"
    await callback.answer(f"Задание #{task_id} {state_str}!", show_alert=True)

    # Return to task detail
    task = await task_repo.get_by_id(task_id)
    if task:
        await callback.message.edit_reply_markup(
            reply_markup=get_admin_task_action_keyboard(task.id, task.is_active)
        )


@router.callback_query(F.data.startswith("adm_del_task:"))
async def handle_admin_del_task(callback: CallbackQuery, task_repo: TaskRepository):
    if not is_admin(callback.from_user.id):
        return

    task_id = int(callback.data.split(":", 1)[1])
    await task_repo.delete_task(task_id)
    await callback.answer(f"Задание #{task_id} удалено!", show_alert=True)
    # Return to tasks list
    await handle_admin_list_tasks(callback, task_repo)


# ---------------- CREATE TASK ----------------
@router.callback_query(F.data == "admin_create_task")
async def handle_admin_create_task_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_task_title)
    await callback.message.edit_text(
        "🎯 <b>СОЗДАНИЕ НОВОГО ЗАДАНИЯ</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Шаг 1/4: Введите <b>название</b> задания:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")]]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_task_title)
async def handle_create_task_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AdminStates.waiting_for_task_desc)
    await message.answer("Шаг 2/4: Введите <b>подробное описание</b> задания:")


@router.message(AdminStates.waiting_for_task_desc)
async def handle_create_task_desc(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    desc = message.text.strip()
    await state.update_data(description=desc)
    await state.set_state(AdminStates.waiting_for_task_cat)
    await message.answer(
        "Шаг 3/4: Введите категорию задания:\n"
        "<code>daily</code> — ежедневное\n"
        "<code>weekly</code> — еженедельное",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_for_task_cat)
async def handle_create_task_cat(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    cat = message.text.strip().lower()
    if cat not in ("daily", "weekly"):
        await message.answer("⚠️ Введите <code>daily</code> или <code>weekly</code>:", parse_mode="HTML")
        return

    await state.update_data(category=cat)
    await state.set_state(AdminStates.waiting_for_task_reward)
    await message.answer("Шаг 4/4: Введите количество XP за выполнение (например, <code>50</code>):", parse_mode="HTML")


@router.message(AdminStates.waiting_for_task_reward)
async def handle_create_task_reward(message: Message, state: FSMContext, task_repo: TaskRepository):
    if not is_admin(message.from_user.id):
        return

    raw = message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("⚠️ Награда должна быть положительным числом:")
        return

    reward_xp = int(raw)
    data = await state.get_data()
    await state.clear()

    task = await task_repo.create_task(
        title=data["title"],
        description=data["description"],
        category=data["category"],
        reward_xp=reward_xp,
        condition_type="manual",
        condition_target=1
    )

    await message.answer(
        f"✅ <b>ЗАДАНИЕ УСПЕШНО СОЗДАНО!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"ID: <code>{task.id}</code>\n"
        f"Название: <b>{task.title}</b>\n"
        f"Категория: <b>{task.category}</b>\n"
        f"Награда: <b>+{task.reward_xp} XP</b>\n"
        f"━━━━━━━━━━━━━━━━━━━",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


# ---------------- BROADCAST ----------------
@router.callback_query(F.data == "admin_broadcast")
async def handle_admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return

    await state.set_state(AdminStates.waiting_for_broadcast_msg)
    await callback.message.edit_text(
        "📢 <b>МАССОВАЯ РАССЫЛКА</b>\n━━━━━━━━━━━━━━━━━━━\n"
        "Отправьте текст сообщения для рассылки всем пользователям бота (поддерживается HTML-разметка):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="admin_panel")]]
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast_msg)
async def handle_admin_broadcast_send(
    message: Message,
    state: FSMContext,
    user_repo: UserRepository,
    bot: Bot
):
    if not is_admin(message.from_user.id):
        return

    text = message.text
    await state.clear()

    user_ids = await user_repo.get_all_telegram_ids()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Рассылка запущена... Всего получателей: {len(user_ids)}")

    for uid in user_ids:
        try:
            await bot.send_message(
                chat_id=uid,
                text=f"📢 <b>ОБЪЯВЛЕНИЕ LEVELUP</b>\n━━━━━━━━━━━━━━━━━━━\n{text}\n━━━━━━━━━━━━━━━━━━━",
                parse_mode="HTML"
            )
            sent += 1
            await asyncio.sleep(0.05)  # Telegram rate limit safety
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ <b>РАССЫЛКА ЗАВЕРШЕНА!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"• Всего пользователей: <b>{len(user_ids)}</b>\n"
        f"• Успешно доставлено: <b>{sent}</b>\n"
        f"• Ошибок отправки: <b>{failed}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode="HTML"
    )


# ---------------- XP AUDIT ----------------
@router.callback_query(F.data == "admin_xp_audit")
async def handle_admin_xp_audit(callback: CallbackQuery, xp_repo: XPRepository):
    if not is_admin(callback.from_user.id):
        return

    # Recent 10 XP events from DB
    async with xp_repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM xp_events ORDER BY created_at DESC LIMIT 10;"
        )

    if not rows:
        await callback.message.edit_text("Лог начислений XP пуст.", reply_markup=get_admin_panel_keyboard())
        await callback.answer()
        return

    lines = []
    for r in rows:
        sign = "+" if r["amount"] > 0 else ""
        created_raw = r["created_at"]
        time_str = created_raw.strftime("%d.%m %H:%M") if hasattr(created_raw, "strftime") else str(created_raw)[:16]
        lines.append(f"• [ID {r['user_id']}] <b>{sign}{r['amount']} XP</b> — {r['reason']} ({time_str})")

    audit_text = "\n".join(lines)
    text = (
        "📜 <b>ПОСЛЕДНИЕ СОБЫТИЯ XP (АУДИТ)</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"{audit_text}\n"
        "━━━━━━━━━━━━━━━━━━━"
    )
    back_kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_panel")]]
    )
    await callback.message.edit_text(text=text, reply_markup=back_kb, parse_mode="HTML")
    await callback.answer()
