from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from db.models import Ticket, TicketType, GuestBooking
from db.session import SessionLocal
from services.tickets import create_ticket
from services.admins import notify_admins_about_ticket
from services.guest_context import (
    deactivate_expired_guest_bookings as _deactivate_expired_guest_bookings,
    get_active_guest_booking,
    get_local_today,
)
from bot.navigation import VIEW_IN_HOUSE, VIEW_PRE_ARRIVAL, VIEW_SEGMENT, nav_reset
from bot.states import FlowState
from services.content import content_manager

router = Router()
MAX_MANUAL_PAST_STAY_DAYS = 30


def deactivate_expired_guest_bookings() -> int:
    return _deactivate_expired_guest_bookings()


def get_or_create_guest_booking(telegram_id: str) -> GuestBooking | None:
    """Backward-compatible alias for active guest booking lookup."""
    return get_active_guest_booking(telegram_id)

@router.callback_query(F.data == "segment_pre_arrival")
async def welcome_pre_arrival(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    await _handle_pre_arrival_logic(callback.message, state)


@router.message(F.text == "Я планирую поездку")
async def welcome_pre_arrival_text(message: Message, state: FSMContext):
    await _handle_pre_arrival_logic(message, state)


async def _handle_pre_arrival_logic(message: Message, state: FSMContext):
    await state.set_state(FlowState.pre_arrival_menu)
    await state.update_data(contact_admin_type="interested", preferred_segment="pre_arrival")
    await nav_reset(state, VIEW_SEGMENT, VIEW_PRE_ARRIVAL)
    text = content_manager.get_text("menus.pre_arrival_title")
    from bot.keyboards.main_menu import build_pre_arrival_reply_keyboard
    await message.answer(text, reply_markup=build_pre_arrival_reply_keyboard())


@router.callback_query(F.data == "segment_in_house")
async def welcome_in_house(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    await _handle_in_house_logic(callback.message, state, str(callback.from_user.id))


@router.message(F.text == "Я уже проживаю в отеле")
async def welcome_in_house_text(message: Message, state: FSMContext):
    await _handle_in_house_logic(message, state, str(message.from_user.id))


async def _handle_in_house_logic(message: Message, state: FSMContext, telegram_id: str):
    existing_booking = get_or_create_guest_booking(telegram_id)
    await state.update_data(contact_admin_type="guest", preferred_segment="in_house")
    await nav_reset(state, VIEW_SEGMENT, VIEW_IN_HOUSE)
    
    # WiFi message
    text = (
        "🏠 <b>Добро пожаловать в GORA!</b>\n\n"
        "🔑 <b>Wi-Fi в отеле:</b>\n"
        "Сеть: <code>GORA_HOTEL_GUEST</code>\n"
        "Пароль: <code>gora2024</code>\n\n"
        "☕ Завтраки проходят с 08:00 до 10:00 в ресторане на 1 этаже."
    )
    
    from bot.keyboards.main_menu import build_in_house_menu, build_guest_booking_keyboard, build_in_house_reply_keyboard
    await state.set_state(FlowState.in_house_menu)
    await message.answer(text, parse_mode="HTML", reply_markup=build_in_house_reply_keyboard())
    
    # Always send the in-house menu so the user can see Room Service and other buttons
    await message.answer(
        content_manager.get_text("menus.in_house_title"),
        reply_markup=build_in_house_menu()
    )
    
    # If no booking registered, prompt to set up stay info
    if not existing_booking:
        await message.answer(
            "📝 <b>Удобная опция:</b>\n\n"
            "Для доступа к Рум-сервису, пожалуйста, укажите данные вашего проживания.",
            reply_markup=build_guest_booking_keyboard(),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "in_check_in")
async def start_check_in(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    await callback.message.answer(
        "📸 <b>БЫСТРАЯ РЕГИСТРАЦИЯ</b>\n\n"
        "Пожалуйста, пришлите фото вашего паспорта (главный разворот). "
        "Это ускорит ваше заселение!",
        parse_mode="HTML"
    )
    await state.set_state("check_in_passport")

@router.message(F.photo, F.state == "check_in_passport")
async def handle_passport(message: Message, state: FSMContext):
    ticket = create_ticket(
        type_=TicketType.CHECK_IN,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        initial_message="📸 Прислано фото паспорта для регистрации"
    )
    await message.answer(f"✅ Фото получено! Мы подготовим документы к вашему приходу. Номер вашей заявки: #{ticket.id}")
    await notify_admins_about_ticket(message.bot, ticket, f"📸 Новый паспорт для регистрации от {message.from_user.full_name}")
    await state.clear()


# --- Guest Booking Flow (Room + Dates) ---

@router.callback_query(F.data == "guest_booking_start")
async def start_guest_booking(callback: CallbackQuery, state: FSMContext):
    """Start guest booking capture flow."""
    await callback.answer()
    await state.set_state(FlowState.guest_room_number)
    text = content_manager.get_text("guest_booking.room_prompt")
    await callback.message.answer(text)


@router.message(FlowState.guest_room_number)
async def handle_guest_room_number(message: Message, state: FSMContext):
    """Handle room number input."""
    room_number = message.text.strip()
    await state.update_data(guest_room_number=room_number)
    await state.set_state(FlowState.guest_check_in_date)
    text = content_manager.get_text("guest_booking.check_in_prompt")
    await message.answer(text)


@router.message(FlowState.guest_check_in_date)
async def handle_guest_check_in(message: Message, state: FSMContext):
    """Handle check-in date input."""
    date_text = message.text.strip()
    
    # Try to parse date (DD.MM.YYYY)
    try:
        check_in = datetime.strptime(date_text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        return

    if check_in < get_local_today() - timedelta(days=MAX_MANUAL_PAST_STAY_DAYS):
        await message.answer(
            "❌ Дата заезда выглядит слишком старой. "
            f"Укажите дату не раньше чем за {MAX_MANUAL_PAST_STAY_DAYS} дней до сегодняшнего дня."
        )
        return
    
    await state.update_data(guest_check_in=check_in.isoformat())
    await state.set_state(FlowState.guest_check_out_date)
    text = content_manager.get_text("guest_booking.check_out_prompt")
    await message.answer(text)


@router.message(FlowState.guest_check_out_date)
async def handle_guest_check_out(message: Message, state: FSMContext):
    """Handle check-out date and save booking."""
    date_text = message.text.strip()
    today = get_local_today()
    
    # Try to parse date (DD.MM.YYYY)
    try:
        check_out = datetime.strptime(date_text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer("❌ Неверный формат. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ")
        return
    
    data = await state.get_data()
    room_number = data.get("guest_room_number")
    check_in_str = data.get("guest_check_in")
    check_in = datetime.fromisoformat(check_in_str).date()
    
    # Validate dates
    if check_out <= check_in:
        await message.answer("❌ Дата выезда должна быть позже даты заезда.")
        return

    if check_out < today:
        await message.answer("❌ Дата выезда уже прошла. Укажите актуальную дату выезда.")
        return
    
    telegram_id = str(message.from_user.id)
    
    # Deactivate any existing bookings
    with SessionLocal() as db:
        db.query(GuestBooking).filter(
            GuestBooking.telegram_id == telegram_id,
            GuestBooking.is_active == True
        ).update({"is_active": False})
        
        # Create new booking
        booking = GuestBooking(
            telegram_id=telegram_id,
            room_number=room_number,
            check_in_date=check_in,
            check_out_date=check_out,
            is_active=True,
            checkin_notified=False,
            checkout_notified=False,
        )
        db.add(booking)
        db.commit()
    
    # Format dates for display
    check_in_display = check_in.strftime("%d.%m.%Y")
    check_out_display = check_out.strftime("%d.%m.%Y")
    
    text = content_manager.get_text("guest_booking.booking_saved").format(
        room_number=room_number,
        check_in=check_in_display,
        check_out=check_out_display
    )
    
    await message.answer(text, parse_mode="HTML")
    
    # Show main in-house menu
    from bot.keyboards.main_menu import build_in_house_menu
    await state.set_state(FlowState.in_house_menu)
    await message.answer(
        content_manager.get_text("menus.in_house_title"),
        reply_markup=build_in_house_menu()
    )
