from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.orm import Session

from db.models import Staff, StaffRole, StaffTask
from db.session import SessionLocal
from bot.utils.reply_texts import button_text

router = Router()


def _get_staff_by_message(db: Session, message: Message) -> Staff | None:
    if not message.from_user:
        return None
    telegram_id = str(message.from_user.id)
    return (
        db.query(Staff)
        .filter(
            Staff.telegram_id == telegram_id,
            Staff.is_active == True,
        )
        .first()
    )


def _build_tasks_keyboard(tasks: list[StaffTask]) -> InlineKeyboardMarkup:
    rows = []
    for task in tasks:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"✅ Закрыть #{task.id}",
                    callback_data=f"staff_close:{task.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=button_text("staff_inline_refresh"), callback_data="staff_refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_task(task: StaffTask) -> str:
    lines = [
        f"🆔 <b>#{task.id}</b> | 🏨 Номер: <b>{task.room_number}</b>",
        f"📌 Тип: <b>{task.task_type}</b>",
    ]
    if task.scheduled_at:
        lines.append(f"🕒 Выполнить до: <b>{task.scheduled_at.strftime('%d.%m.%Y %H:%M')}</b>")
    if task.description:
        lines.append(f"📝 {task.description}")
    return "\n".join(lines)


async def _send_staff_tasks(message: Message, db: Session, staff: Staff) -> None:
    tasks = (
        db.query(StaffTask)
        .filter(
            StaffTask.status == "PENDING",
            StaffTask.assigned_to == str(staff.telegram_id),
        )
        .order_by(StaffTask.created_at.asc())
        .all()
    )

    if not tasks:
        await message.answer("🛠 <b>Мои задачи</b>\n\nАктивных задач пока нет.")
        return

    text = "🛠 <b>Мои активные задачи</b>\n\n" + "\n\n".join(_format_task(task) for task in tasks)
    await message.answer(text, parse_mode="HTML", reply_markup=_build_tasks_keyboard(tasks))


@router.message(F.text == "/tasks")
@router.message(F.text == "/staff")
@router.message(F.text.func(lambda value: value == button_text("staff_tasks")))
@router.message(F.text.func(lambda value: value == button_text("staff_refresh")))
async def show_staff_tasks(message: Message):
    db = SessionLocal()
    try:
        staff = _get_staff_by_message(db, message)
        if not staff or staff.role == StaffRole.ADMINISTRATOR:
            await message.answer("Доступно только для сотрудников.")
            return
        await _send_staff_tasks(message, db, staff)
    finally:
        db.close()


@router.callback_query(F.data == "staff_refresh")
async def refresh_staff_tasks(callback: CallbackQuery):
    if not callback.message or not callback.from_user:
        return

    db = SessionLocal()
    try:
        staff = (
            db.query(Staff)
            .filter(Staff.telegram_id == str(callback.from_user.id), Staff.is_active == True)
            .first()
        )
        if not staff:
            await callback.answer("Нет доступа", show_alert=True)
            return

        tasks = (
            db.query(StaffTask)
            .filter(StaffTask.status == "PENDING", StaffTask.assigned_to == str(staff.telegram_id))
            .order_by(StaffTask.created_at.asc())
            .all()
        )

        if not tasks:
            await callback.message.edit_text("🛠 <b>Мои задачи</b>\n\nАктивных задач пока нет.", parse_mode="HTML")
        else:
            text = "🛠 <b>Мои активные задачи</b>\n\n" + "\n\n".join(_format_task(task) for task in tasks)
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_build_tasks_keyboard(tasks))
        await callback.answer("Обновлено")
    finally:
        db.close()


@router.callback_query(F.data.startswith("staff_close:"))
async def close_staff_task(callback: CallbackQuery):
    if not callback.from_user:
        return

    task_id_raw = (callback.data or "").split(":", 1)[1]
    if not task_id_raw.isdigit():
        await callback.answer("Некорректный ID", show_alert=True)
        return
    task_id = int(task_id_raw)

    db = SessionLocal()
    try:
        staff = (
            db.query(Staff)
            .filter(Staff.telegram_id == str(callback.from_user.id), Staff.is_active == True)
            .first()
        )
        if not staff:
            await callback.answer("Нет доступа", show_alert=True)
            return

        task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
        if not task:
            await callback.answer("Задача не найдена", show_alert=True)
            return
        if str(task.assigned_to) != str(staff.telegram_id):
            await callback.answer("Это не ваша задача", show_alert=True)
            return

        task.status = "COMPLETED"
        task.completed_at = datetime.utcnow()
        db.commit()

        tasks = (
            db.query(StaffTask)
            .filter(StaffTask.status == "PENDING", StaffTask.assigned_to == str(staff.telegram_id))
            .order_by(StaffTask.created_at.asc())
            .all()
        )
        if callback.message:
            if not tasks:
                await callback.message.edit_text("🛠 <b>Мои задачи</b>\n\nАктивных задач пока нет.", parse_mode="HTML")
            else:
                text = "🛠 <b>Мои активные задачи</b>\n\n" + "\n\n".join(_format_task(item) for item in tasks)
                await callback.message.edit_text(text, parse_mode="HTML", reply_markup=_build_tasks_keyboard(tasks))

        await callback.answer(f"Задача #{task.id} закрыта")
    finally:
        db.close()
