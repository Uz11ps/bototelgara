from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.states import FlowState
from services.content import content_manager


router = Router()


@router.callback_query(FlowState.pre_arrival_menu)
async def handle_pre_arrival_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle clicks in the pre-arrival menu.

    For Milestone A we respond with simple informational texts from content.
    """
    await callback.answer()  # Acknowledge immediately to prevent freezing

    key = callback.data or ""
    
    if key == "pre_contact_admin":
        await _handle_pre_contact_admin_logic(callback.message, state, prefer_interested=True)
        return
    if key.startswith("pre_") and "admin" in key.lower():
        await _handle_pre_contact_admin_logic(callback.message, state, prefer_interested=True)
        return
    if key == "pre_how_to_get":
        await _handle_pre_how_to_get_logic(callback.message)
        return
    if key == "pre_faq":
        await _handle_pre_faq_logic(callback.message)
        return
    if key == "pre_events_banquets":
        from bot.handlers.events import show_events
        await show_events(callback, state)
        return
    
    mapping = {
        "pre_book_room": "pre_arrival.book_room",
        "pre_about_hotel": "pre_arrival.about_hotel",
        "pre_restaurant": "pre_arrival.restaurant",
    }

    text_key = mapping.get(key)
    if not text_key:
        return

    await _handle_pre_arrival_text_key_logic(callback.message, text_key)


@router.callback_query(F.data == "pre_contact_admin")
async def handle_pre_contact_admin_any_state(callback: CallbackQuery, state: FSMContext) -> None:
    """Fallback handler for admin contact from pre-arrival regardless of FSM state."""
    await callback.answer()
    await _handle_pre_contact_admin_logic(callback.message, state, prefer_interested=True)


@router.callback_query(F.data == "checkout_contact_admin")
async def handle_checkout_contact_admin(callback: CallbackQuery, state: FSMContext) -> None:
    """Open admin contact flow from checkout notification."""
    await callback.answer()
    await state.update_data(contact_admin_type="guest")
    await _handle_pre_contact_admin_logic(callback.message, state, prefer_interested=False)


@router.callback_query(F.data.func(lambda d: bool(d) and d.startswith("pre_") and "admin" in d.lower()))
async def handle_pre_contact_admin_any_pre_admin_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Robust fallback for edited pre-arrival admin callback names."""
    await callback.answer()
    await _handle_pre_contact_admin_logic(callback.message, state, prefer_interested=True)


async def _handle_pre_contact_admin_logic(message: Message, state: FSMContext, prefer_interested: bool = False):
    data = await state.get_data()
    contact_type = "interested" if prefer_interested else data.get("contact_admin_type")
    if contact_type not in {"guest", "interested"}:
        from db.models import GuestBooking
        from db.session import SessionLocal

        with SessionLocal() as db:
            booking = db.query(GuestBooking).filter(
                GuestBooking.telegram_id == str(message.from_user.id),
                GuestBooking.is_active == True,
            ).first()
        contact_type = "guest" if booking else "interested"
    await state.update_data(contact_admin_type=contact_type)

    if contact_type == "guest":
        # For in-house guests we should open admin dialog directly,
        # not redirect to room-service flow with booking checks.
        await state.set_state(FlowState.contact_admin_message)
        await message.answer("Напишите ваш вопрос, и администратор ответит в этом же диалоге.")
        return

    await state.set_state(FlowState.contact_admin_interested_choice)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Позвоните мне", callback_data="int_admin_call")],
        [InlineKeyboardButton(text="✉️ Связаться с администратором", callback_data="int_admin_message")],
        [InlineKeyboardButton(text="🏨 Забронировать номер", callback_data="int_admin_booking")],
    ])
    await message.answer("Выберите удобный вариант связи:", reply_markup=kb)


@router.callback_query(F.data.in_({"int_admin_call", "int_admin_message", "int_admin_booking"}))
async def handle_interested_admin_choice(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    key = callback.data or ""
    if key == "int_admin_booking":
        from bot.handlers.booking import _handle_booking_logic
        await _handle_booking_logic(callback.message, state)
        return

    if key == "int_admin_message":
        await state.update_data(contact_admin_type="interested")
        await state.set_state(FlowState.contact_admin_message)
        await callback.message.answer("Напишите ваш вопрос, и администратор свяжется с вами.")
        return

    from aiogram import Bot
    from db.models import TicketType
    from services.admins import notify_admins_about_ticket
    from services.guest_context import get_active_room_number
    from services.tickets import TicketRateLimitExceededError, create_ticket

    summary = "Запрос обратного звонка от гостя (Ищу отель)."
    payload = {"branch": "contact_admin_call_me", "user_type": "interested"}
    room_number = get_active_room_number(str(callback.from_user.id))
    try:
        ticket = create_ticket(
            type_=TicketType.PRE_ARRIVAL,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=room_number,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        await callback.message.answer("Вы отправили слишком много заявок. Пожалуйста, подождите.")
        return

    await callback.message.answer(f"Спасибо, запрос на звонок принят. Номер заявки: #{ticket.id}.")
    bot: Bot = callback.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)


async def _handle_pre_how_to_get_logic(message: Message):
    await message.answer(
        "📍 Как добраться:\n<a href=\"https://yandex.com/maps/-/CPa0qU8F\">Открыть маршрут в Яндекс.Картах</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    from bot.keyboards.main_menu import build_pre_arrival_reply_keyboard
    await message.answer(
        content_manager.get_text("menus.pre_arrival_title"),
        reply_markup=build_pre_arrival_reply_keyboard(),
    )


async def _handle_pre_faq_logic(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    # Кнопка открывает в браузере; на iOS/Android якорь #faq иногда не срабатывает —
    # на сайте нужно id="faq" у секции «Ответы на частые вопросы»
    faq_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Открыть FAQ на сайте", url="https://gora-hotel.ru/#faq")],
    ])
    await message.answer(
        "❓ <b>Ответы на частые вопросы</b>\n\n"
        "Нажмите кнопку ниже, чтобы открыть раздел FAQ на сайте отеля.\n"
        "Если страница открылась вверху — прокрутите вниз до раздела «Ответы на частые вопросы».",
        parse_mode="HTML",
        reply_markup=faq_kb,
    )
    from bot.keyboards.main_menu import build_pre_arrival_reply_keyboard
    await message.answer(
        content_manager.get_text("menus.pre_arrival_title"),
        reply_markup=build_pre_arrival_reply_keyboard(),
    )


async def _handle_pre_arrival_text_key_logic(message: Message, text_key: str):
    text = content_manager.get_text(text_key)
    await message.answer(text)
    from bot.keyboards.main_menu import build_pre_arrival_reply_keyboard
    await message.answer(
        content_manager.get_text("menus.pre_arrival_title"),
        reply_markup=build_pre_arrival_reply_keyboard(),
    )


@router.callback_query(FlowState.contact_admin_type)
async def handle_contact_admin_type_pre_arrival(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle selection of user type when contacting admin (from pre-arrival menu)."""
    await callback.answer()  # Acknowledge immediately to prevent freezing
    from aiogram import Bot
    from db.models import TicketType
    from services.admins import notify_admins_about_ticket
    from services.tickets import TicketRateLimitExceededError, create_ticket
    
    key = callback.data or ""
    
    if key == "contact_admin_guest":
        user_type = "Гость"
        await state.update_data(contact_admin_type="guest")
    elif key == "contact_admin_interested":
        user_type = "Ищу отель"
        await state.update_data(contact_admin_type="interested")
    else:
        return
    
    await state.set_state(FlowState.contact_admin_message)
    await callback.message.answer(f"Вы выбрали: {user_type}\n\nНапишите ваш вопрос или запрос:")


@router.message(FlowState.contact_admin_message)
async def handle_contact_admin_message_pre_arrival(message: Message, state: FSMContext) -> None:
    """Create ticket for admin contact request (from pre-arrival menu)."""
    from aiogram import Bot
    from db.models import TicketType
    from db.session import SessionLocal
    from services.admins import notify_admins_about_ticket
    from services.guest_context import get_active_room_number
    from services.tickets import (
        TicketRateLimitExceededError,
        append_guest_message_to_ticket,
        create_ticket,
        get_open_dialog_ticket_for_guest,
    )
    
    user_message = message.text or ""
    data = await state.get_data()
    user_type = data.get("contact_admin_type", "guest")
    guest_chat_id = str(message.from_user.id)
    room_number = get_active_room_number(guest_chat_id)
    
    user_type_label = "Гость" if user_type == "guest" else "Ищу отель"
    
    payload = {
        "branch": "contact_admin",
        "user_type": user_type,
        "message": user_message,
    }
    
    summary = f"Запрос к администратору ({user_type_label}): {user_message}"
    
    try:
        with SessionLocal() as session:
            open_ticket = get_open_dialog_ticket_for_guest(session, guest_chat_id)
        if open_ticket:
            ticket = append_guest_message_to_ticket(ticket_id=open_ticket.id, content=summary)
            if ticket is not None:
                confirmation = (
                    f"💬 Ваше сообщение добавлено в открытый диалог #{ticket.id}. "
                    "Администратор ответит в этом же чате."
                )
                notify_summary = f"Новое сообщение в открытом диалоге #{ticket.id}: {user_message}"
            else:
                open_ticket = None
        if not open_ticket:
            ticket = create_ticket(
                type_=TicketType.PRE_ARRIVAL,
                guest_chat_id=guest_chat_id,
                guest_name=message.from_user.full_name,
                room_number=room_number,
                payload=payload,
                initial_message=summary,
                dialog_open=True,
                dialog_timeout_seconds=3600,
            )
            confirmation = (
                f"Спасибо, открытый диалог #{ticket.id} создан. "
                "Пишите сюда — сообщения будут добавляться в этот же диалог."
            )
            notify_summary = summary
    except TicketRateLimitExceededError:
        warning = "Вы отправили слишком много заявок. Пожалуйста, подождите."
        from bot.keyboards.main_menu import build_main_reply_keyboard
        await message.answer(warning)
        await state.clear()
        await message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=build_main_reply_keyboard()
        )
        return
    
    await message.answer(confirmation)
    
    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, notify_summary)
    
    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )
