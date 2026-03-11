from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from db.session import SessionLocal
from db.models import StaffTask, Staff, User
from services.phone_utils import normalize_phone, phones_match

router = Router()

@router.message(F.text.in_({"👷‍♂️ Вход для сотрудников", "👷‍♂️ Сотрудникам"}))
async def staff_login_request_contact(message: Message, state: FSMContext):
    """Ask staff member to share their phone number."""
    await state.update_data(phone_share_context="staff_login")
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)],
            [KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Для входа в панель сотрудника, пожалуйста, поделитесь вашим номером телефона. "
        "Это нужно для привязки вашего Telegram к профилю сотрудника.",
        reply_markup=kb
    )

@router.message(F.contact)
async def staff_login_process_contact(message: Message, state: FSMContext):
    """Save shared phone and continue the appropriate flow."""
    contact = message.contact
    if contact.user_id != message.from_user.id:
        await message.answer("Пожалуйста, отправьте свой собственный номер телефона, используя кнопку ниже.")
        return

    phone = normalize_phone(contact.phone_number)
    telegram_id = str(message.from_user.id)
    data = await state.get_data()
    share_context = data.get("phone_share_context")

    matched_staff_id = None
    matched_staff_name = None
    with SessionLocal() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            user = User(
                telegram_id=telegram_id,
                full_name=message.from_user.full_name,
                phone=phone,
            )
            db.add(user)
        else:
            user.phone = phone
            if not user.full_name:
                user.full_name = message.from_user.full_name

        if share_context == "staff_login":
            staff_members = db.query(Staff).all()
            matched_staff = None
            for staff_member in staff_members:
                if staff_member.phone and phones_match(staff_member.phone, phone):
                    matched_staff = staff_member
                    break

            if matched_staff:
                matched_staff.telegram_id = telegram_id
                matched_staff_id = matched_staff.id
                matched_staff_name = matched_staff.full_name

        db.commit()

    await state.update_data(phone_share_context=None)

    if share_context != "staff_login":
        await message.answer(
            "✅ Номер телефона сохранен. "
            "Если на этот номер есть бронирование в Shelter, бот автоматически найдет его при синхронизации."
        )
        try:
            from services.shelter_sync import sync_reservations_once

            await sync_reservations_once()
        except Exception:
            pass

        preferred_segment = data.get("preferred_segment")
        if preferred_segment == "in_house":
            from bot.handlers.check_in import _handle_in_house_logic

            await _handle_in_house_logic(message, state, telegram_id)
            return
        if preferred_segment == "pre_arrival":
            from bot.handlers.check_in import _handle_pre_arrival_logic

            await _handle_pre_arrival_logic(message, state)
            return

        from bot.handlers.start import _show_segment_selection

        await _show_segment_selection(message, state)
        return

    if matched_staff_id is None:
        from bot.keyboards.main_menu import build_segment_reply_keyboard
        await message.answer(
            "✅ Номер телефона сохранен. "
            "Если на этот номер есть бронирование в Shelter, бот автоматически найдет его при синхронизации.",
            reply_markup=build_segment_reply_keyboard(),
        )
        return

    from bot.keyboards.main_menu import build_staff_reply_keyboard
    await message.answer(
        f"✅ Авторизация успешна! Добро пожаловать, {matched_staff_name}.\n\n"
        "Теперь вы будете получать уведомления о новых задачах прямо в этот чат.",
        reply_markup=build_staff_reply_keyboard()
    )

    # Automatically show tasks
    db = SessionLocal()
    try:
        await send_staff_tasks(message, db, matched_staff_id)
    finally:
        db.close()

@router.message(F.text == "📋 Мои задачи")
async def handle_my_tasks(message: Message):
    db = SessionLocal()
    staff = db.query(Staff).filter(Staff.telegram_id == str(message.from_user.id)).first()
    if not staff:
        from bot.keyboards.main_menu import build_main_reply_keyboard
        await message.answer("Вы не авторизованы как сотрудник.", reply_markup=build_main_reply_keyboard())
        db.close()
        return

    await send_staff_tasks(message, db, staff.id)
    db.close()

@router.message(F.text == "🚪 Выйти из профиля сотрудника")
async def handle_staff_logout(message: Message):
    db = SessionLocal()
    staff = db.query(Staff).filter(Staff.telegram_id == str(message.from_user.id)).first()
    if staff:
        staff.telegram_id = None
        db.commit()
    db.close()

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await message.answer(
        "Вы вышли из профиля сотрудника. Уведомления о задачах отключены.",
        reply_markup=build_main_reply_keyboard()
    )

async def send_staff_tasks(message: Message, db, staff_id: int):
    tasks = db.query(StaffTask).filter(
        StaffTask.status == "PENDING", 
        StaffTask.assigned_to == str(staff_id)
    ).all()
    
    if not tasks:
        await message.answer("Активных задач пока нет. Отдыхайте!")
        return

    await message.answer("🛠 <b>Ваши текущие задачи:</b>", parse_mode="HTML")
    for task in tasks:
        text = f"📍 Номер {task.room_number}: {task.task_type}\n{task.description or ''}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнить", callback_data=f"complete_task_{task.id}")]
        ])
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("complete_task_"))
async def complete_staff_task(callback: CallbackQuery):
    task_id = int(callback.data.replace("complete_task_", ""))
    
    db = SessionLocal()
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    
    if not task:
        await callback.answer("Задача не найдена.", show_alert=True)
        db.close()
        return

    if task.status != "PENDING":
        await callback.answer("Эта задача уже закрыта.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        db.close()
        return

    # Check if the user is the assigned staff member
    staff = db.query(Staff).filter(Staff.telegram_id == str(callback.from_user.id)).first()
    if not staff or task.assigned_to != str(staff.id):
        await callback.answer("Вы не можете закрыть эту задачу.", show_alert=True)
        db.close()
        return

    # Update task status
    task.status = "COMPLETED"
    from datetime import datetime
    task.completed_at = datetime.utcnow()
    db.commit()
    db.close()

    await callback.message.edit_text(
        callback.message.html_text + "\n\n<b>✅ ВЫПОЛНЕНО</b>",
        parse_mode="HTML",
        reply_markup=None
    )
    await callback.answer("Задача отмечена как выполненная!")
