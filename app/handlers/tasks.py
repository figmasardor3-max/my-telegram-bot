import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from app.database.repositories.tasks import TaskRepository
from app.services.tasks import TaskService
from app.keyboards.inline import (
    get_tasks_menu_keyboard,
    get_task_detail_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="tasks_handler")


async def render_tasks_view(
    user_id: int,
    category: str,
    task_service: TaskService
) -> tuple[str, any]:
    tasks_data = await task_service.get_tasks_with_status(user_id, category=category)
    cat_title = "ЕЖЕДНЕВНЫЕ ЗАДАНИЯ (DAILY)" if category == "daily" else "ЕЖЕНЕДЕЛЬНЫЕ ЗАДАНИЯ (WEEKLY)"

    completed_count = sum(1 for t in tasks_data if t["is_completed"])
    total_count = len(tasks_data)

    text = (
        f"🎯 <b>{cat_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Выполняйте задания, чтобы регулярно повышать уровень и открывать достижения.\n\n"
        f"Статус выполнения: <b>{completed_count} / {total_count}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Выберите задание из списка ниже для просмотра условий:</i>"
    )

    markup = get_tasks_menu_keyboard(category, tasks_data)
    return text, markup


@router.message(F.text == "🎯 Задания")
async def handle_tasks_message(message: Message, task_service: TaskService):
    text, markup = await render_tasks_view(message.from_user.id, "daily", task_service)
    await message.answer(text=text, reply_markup=markup, parse_mode="HTML")


@router.callback_query(F.data == "nav_tasks")
async def handle_nav_tasks(callback: CallbackQuery, task_service: TaskService):
    text, markup = await render_tasks_view(callback.from_user.id, "daily", task_service)
    try:
        await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text=text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("tasks_cat:"))
async def handle_tasks_category(callback: CallbackQuery, task_service: TaskService):
    category = callback.data.split(":", 1)[1]
    text, markup = await render_tasks_view(callback.from_user.id, category, task_service)
    await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("task_view:"))
async def handle_task_view(
    callback: CallbackQuery,
    task_repo: TaskRepository
):
    task_id = int(callback.data.split(":", 1)[1])
    task = await task_repo.get_by_id(task_id)
    if not task:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    user_task = await task_repo.get_user_task(callback.from_user.id, task_id)
    is_done = user_task is not None

    status_str = "✅ <b>ВЫПОЛНЕНО</b>" if is_done else "⚡ <b>ДОСТУПНО ДЛЯ ВЫПОЛНЕНИЯ</b>"

    text = (
        f"🎯 <b>ЗАДАНИЕ: {task.title.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Категория: <b>{task.category.upper()}</b>\n"
        f"Награда: <b>+{task.reward_xp} XP</b>\n"
        f"Статус: {status_str}\n\n"
        f"📝 <b>Описание:</b>\n"
        f"{task.description}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )

    markup = get_task_detail_keyboard(task.id, is_done, task.category)
    await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("task_claim:"))
async def handle_task_claim(
    callback: CallbackQuery,
    task_service: TaskService,
    task_repo: TaskRepository,
    bot: Bot
):
    task_id = int(callback.data.split(":", 1)[1])
    success, msg, _ = await task_service.complete_and_claim_task(callback.from_user.id, task_id, bot)

    await callback.answer(msg.split("\n")[0] if "\n" in msg else msg, show_alert=True)

    # Refresh task view
    task = await task_repo.get_by_id(task_id)
    if task:
        markup = get_task_detail_keyboard(task.id, is_completed=True, category=task.category)
        text = (
            f"🎯 <b>ЗАДАНИЕ: {task.title.upper()}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Категория: <b>{task.category.upper()}</b>\n"
            f"Награда: <b>+{task.reward_xp} XP</b>\n"
            f"Статус: ✅ <b>ВЫПОЛНЕНО</b>\n\n"
            f"📝 <b>Описание:</b>\n"
            f"{task.description}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎉 <i>Награда успешно получена!</i>"
        )
        try:
            await callback.message.edit_text(text=text, reply_markup=markup, parse_mode="HTML")
        except Exception:
            pass
