from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from bot.states import FlowState
from bot.utils.reply_keyboards import build_role_reply_keyboard
from bot.utils.reply_texts import button_text
from services.content import content_manager


router = Router()


from datetime import datetime

def get_current_season() -> str:
    month = datetime.now().month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"

@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    from db.session import SessionLocal
    from db.models import Staff, StaffRole
    from services.tickets import is_user_admin
    from bot.keyboards.main_menu import build_admin_panel_menu, build_staff_reply_keyboard
    
    user_id = str(message.from_user.id)
    
    # 1. Resolve user role and choose correct persistent keyboard
    with SessionLocal() as session:
        is_admin = is_user_admin(session, user_id)
        staff = (
            session.query(Staff)
            .filter(Staff.telegram_id == user_id, Staff.is_active == True)
            .first()
        )
        is_staff_worker = bool(staff and staff.role in {StaffRole.MAID, StaffRole.TECHNICIAN})

    if is_staff_worker:
        staff_text = (
            "🛠 <b>Панель сотрудника</b>\n\n"
            "Используйте кнопки ниже, чтобы открыть и закрыть ваши задачи."
        )
        await message.answer("Обновляю клавиатуру...", reply_markup=ReplyKeyboardRemove())
        await message.answer(staff_text, parse_mode="HTML", reply_markup=build_staff_reply_keyboard())
        await message.answer(f"Нажмите «{button_text('staff_tasks')}», чтобы увидеть активные задачи.")
        return

    # 2. Default user menu for guests/admins
    greeting = content_manager.get_text("greeting.start")
    season = get_current_season()
    seasonal_text = content_manager.get_text(f"seasons.{season}")
    choice_prompt = content_manager.get_text("menus.segment_choice_prompt")

    await message.answer("Обновляю клавиатуру...", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        f"{greeting}\n\n{seasonal_text}\n\n{choice_prompt}", 
        reply_markup=build_role_reply_keyboard(user_id)
    )
    
    # 3. Check if user is admin and show admin panel as a separate message
    with SessionLocal() as session:
        if is_admin:
            from services.tickets import get_pending_tickets, get_all_active_tickets
            pending_count = len(get_pending_tickets(session))
            all_count = len(get_all_active_tickets(session))
            
            admin_greeting = (
                f"👨‍💼 <b>Добро пожаловать в админ-панель отеля GORA</b>\n\n"
                f"📊 Активных заявок: {all_count}\n"
                f"⏳ Ожидают решения: {pending_count}\n\n"
                f"Выберите действие:"
            )
            
            await message.answer(admin_greeting, reply_markup=build_admin_panel_menu(), parse_mode="HTML")


@router.callback_query(F.data == "back_to_segment")
async def back_to_segment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FlowState.choosing_segment)
    # Since main menu is a persistent reply keyboard, we just delete the sub-menu message
    # and remind the user to use the bottom menu.
    await callback.message.delete()
    choice_prompt = content_manager.get_text("menus.segment_choice_prompt")
    await callback.message.answer(choice_prompt)


@router.message(F.text.func(lambda value: value == button_text("main_home")))
async def reply_main_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await cmd_start(message)


@router.message(F.text.func(lambda value: value in {button_text("contact_guest"), button_text("contact_interested")}))
async def reply_admin_type_selection(message: Message, state: FSMContext) -> None:
    """Handle admin type selection from reply keyboard."""

    user_type = "guest" if message.text == button_text("contact_guest") else "interested"
    await state.set_state(FlowState.contact_admin_type)
    await state.update_data(contact_admin_type=user_type)
    
    user_type_label = "Поселенец" if user_type == "guest" else "Заинтересованный человек"
    await state.set_state(FlowState.contact_admin_message)
    await message.answer(f"Вы выбрали: {user_type_label}\n\nНапишите ваш вопрос или запрос:")


@router.message(F.text.func(lambda value: value in {
    button_text("room_technical"),
    button_text("room_extra"),
    button_text("room_cleaning"),
    button_text("room_pillow"),
    button_text("room_other"),
}))
async def reply_room_service_selection(message: Message, state: FSMContext) -> None:
    """Handle room service selection from reply keyboard."""

    mapping = {
        button_text("room_technical"): "rs_technical_problem",
        button_text("room_extra"): "rs_extra_to_room",
        button_text("room_cleaning"): "rs_cleaning",
        button_text("room_pillow"): "rs_pillow_menu",
        button_text("room_other"): "rs_other",
    }
    
    callback_data = mapping.get(message.text)
    if callback_data:
        await state.set_state(FlowState.room_service_room_number)
        await state.update_data(service_branch=callback_data.replace("rs_", ""))
        await message.answer("Укажите номер вашей комнаты:")


@router.message(F.text.func(lambda value: value in {
    button_text("in_room_service"),
    button_text("in_breakfasts"),
    button_text("in_guide"),
    button_text("in_weather"),
    button_text("in_sos"),
    button_text("in_profile"),
}))
async def reply_in_house_menu_selection(message: Message, state: FSMContext) -> None:
    """Handle in-house menu selection from reply keyboard."""

    # Имитируем callback для существующих обработчиков
    if message.text == button_text("in_room_service"):
        await state.set_state(FlowState.room_service_choosing_branch)
        text = content_manager.get_text("room_service.what_do_you_need")
        from bot.keyboards.main_menu import build_room_service_reply_keyboard
        await message.answer(text)
        await message.answer("Используйте кнопки ниже для выбора:", reply_markup=build_room_service_reply_keyboard())
    elif message.text == button_text("in_breakfasts"):
        # Переход к завтракам обрабатывается через callback
        await message.answer("Выберите завтрак из меню выше или используйте кнопки ниже.")
    elif message.text == button_text("in_guide"):
        # Переход к гиду обрабатывается через callback
        await message.answer("Выберите категорию гида из меню выше.")
    elif message.text == button_text("in_weather"):
        # Переход к погоде обрабатывается через callback
        await message.answer("Информация о погоде доступна в меню выше.")
    elif message.text == button_text("in_sos"):
        # Переход к SOS обрабатывается через callback
        await message.answer("Используйте меню выше для обращения за помощью.")
    elif message.text == button_text("in_profile"):
        # Переход к личному кабинету обрабатывается через callback
        await message.answer("Информация о личном кабинете доступна в меню выше.")


@router.message(F.text.func(lambda value: value in {
    button_text("menu_breakfast"),
    button_text("menu_lunch"),
    button_text("menu_dinner"),
    button_text("menu_cart"),
}))
async def reply_menu_selection(message: Message, state: FSMContext) -> None:
    """Handle menu category selection from reply keyboard."""
    from bot.keyboards.main_menu import build_menu_categories_keyboard
    
    mapping = {
        button_text("menu_breakfast"): "menu_cat_breakfast",
        button_text("menu_lunch"): "menu_cat_lunch",
        button_text("menu_dinner"): "menu_cat_dinner",
    }
    
    callback_data = mapping.get(message.text)
    if callback_data:
        # Имитируем callback для обработчика категорий меню
        await message.answer(f"Выбрана категория: {message.text}. Используйте меню выше для выбора блюд.")
    elif message.text == button_text("menu_cart"):
        await message.answer("Просмотр корзины доступен в меню выше.")


@router.message(F.text.func(lambda value: value == button_text("pre_book_room")))
async def reply_book_room(message: Message, state: FSMContext) -> None:
    """Handle booking room from reply keyboard."""
    from datetime import date
    from bot.states import FlowState
    
    # Импортируем функцию календаря из booking.py
    from bot.handlers.booking import build_calendar_keyboard
    
    await state.set_state(FlowState.booking_check_in)
    await message.answer(
        "Выберите дату заезда:",
        reply_markup=build_calendar_keyboard(date.today(), "checkin")
    )


@router.message(F.text.func(lambda value: value in {
    button_text("pre_rooms_prices"),
    button_text("pre_about_hotel"),
    button_text("pre_events"),
    button_text("pre_route"),
    button_text("pre_faq"),
    button_text("pre_restaurant"),
}))
async def reply_pre_arrival_selection(message: Message, state: FSMContext) -> None:
    """Handle pre-arrival menu selection from reply keyboard."""
    from services.content import content_manager
    
    mapping = {
        button_text("pre_rooms_prices"): "pre_arrival.rooms_prices",
        button_text("pre_about_hotel"): "pre_arrival.about_hotel",
        button_text("pre_events"): "pre_arrival.events_banquets",
        button_text("pre_route"): "pre_arrival.how_to_get",
        button_text("pre_faq"): "pre_arrival.faq",
        button_text("pre_restaurant"): "pre_arrival.restaurant",
    }
    
    text_key = mapping.get(message.text)
    if text_key:
        text = content_manager.get_text(text_key)
        await message.answer(text)
        from bot.keyboards.main_menu import build_pre_arrival_reply_keyboard
        await message.answer(content_manager.get_text("menus.pre_arrival_title"))
        await message.answer("Используйте кнопки ниже для навигации:", reply_markup=build_pre_arrival_reply_keyboard())


@router.message(F.text.func(lambda value: value == button_text("main_admin")))
async def reply_admin_contact(message: Message, state: FSMContext) -> None:
    from bot.keyboards.main_menu import build_admin_contact_reply_keyboard
    await state.set_state(FlowState.contact_admin_type)
    await message.answer("Выберите, кто вы:")
    await message.answer("Используйте кнопки ниже для выбора:", reply_markup=build_admin_contact_reply_keyboard())


@router.message(F.text.func(lambda value: value == button_text("main_room_service")))
async def reply_room_service(message: Message, state: FSMContext) -> None:
    from bot.keyboards.main_menu import build_room_service_reply_keyboard
    await state.set_state(FlowState.room_service_choosing_branch)
    text = content_manager.get_text("room_service.what_do_you_need")
    await message.answer(text)
    await message.answer("Используйте кнопки ниже для выбора:", reply_markup=build_room_service_reply_keyboard())


# NOTE: segment_pre_arrival and segment_in_house callbacks are handled in check_in.py


@router.message(Command("reload_content"))
async def reload_content(message: Message) -> None:
    from db.session import SessionLocal
    from db.models import AdminUser

    user_id = str(message.from_user.id)

    with SessionLocal() as session:
        admin = (
            session.query(AdminUser)
            .filter(AdminUser.telegram_id == user_id, AdminUser.is_active == 1)
            .first()
        )

    if admin is None:
        text = content_manager.get_text("system.not_authorized")
        await message.answer(text)
        return

    content_manager.reload()
    text = content_manager.get_text("system.content_reloaded")
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands"""
    from db.session import SessionLocal
    from services.tickets import is_user_admin
    from db.models import Staff, StaffRole
    
    user_id = str(message.from_user.id)
    
    # Check if user is admin/staff
    with SessionLocal() as session:
        is_admin = is_user_admin(session, user_id)
        staff = (
            session.query(Staff)
            .filter(Staff.telegram_id == user_id, Staff.is_active == True)
            .first()
        )
        is_staff_worker = bool(staff and staff.role in {StaffRole.MAID, StaffRole.TECHNICIAN})
    
    if is_admin:
        help_text = (
            "📋 <b>Команды администратора:</b>\n\n"
            "<b>Управление заявками:</b>\n"
            "/admin или /panel - Админ-панель\n"
            "/view_ticket ID - Просмотр заявки\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n\n"
            "<b>Система:</b>\n"
            "/sheltertest - Проверка подключения к Shelter API\n"
            "/reload_content - Перезагрузить контент\n"
            "/help - Показать эту справку\n"
        )
    elif is_staff_worker:
        help_text = (
            "🛠 <b>Команды сотрудника:</b>\n\n"
            "/tasks - Мои активные задачи\n"
            "/staff - Мои активные задачи\n"
            "/start - Показать панель сотрудника\n"
        )
    else:
        help_text = (
            "📋 <b>Доступные команды:</b>\n\n"
            "<b>Основные:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n"
        )
    
    await message.answer(help_text, parse_mode="HTML")
