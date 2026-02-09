from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from bot.keyboards.main_menu import build_pre_arrival_menu, build_contact_admin_type_menu
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
        await state.set_state(FlowState.contact_admin_type)
        await callback.message.answer(
            "Выберите, кто вы:",
            reply_markup=build_contact_admin_type_menu()
        )
        return
    
    mapping = {
        "pre_book_room": "pre_arrival.book_room",
        "pre_rooms_prices": "pre_arrival.rooms_prices",
        "pre_about_hotel": "pre_arrival.about_hotel",
        "pre_events_banquets": "pre_arrival.events_banquets",
        "pre_how_to_get": "pre_arrival.how_to_get",
        "pre_faq": "pre_arrival.faq",
        "pre_restaurant": "pre_arrival.restaurant",
    }

    text_key = mapping.get(key)
    if not text_key:
        return

    text = content_manager.get_text(text_key)
    await callback.message.answer(text)
    await callback.message.answer(
        content_manager.get_text("menus.pre_arrival_title"),
        reply_markup=build_pre_arrival_menu(),
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
        user_type = "Поселенец"
        await state.update_data(contact_admin_type="guest")
    elif key == "contact_admin_interested":
        user_type = "Заинтересованный человек"
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
    from services.admins import notify_admins_about_ticket
    from services.tickets import TicketRateLimitExceededError, create_ticket
    
    user_message = message.text or ""
    data = await state.get_data()
    user_type = data.get("contact_admin_type", "guest")
    
    user_type_label = "Поселенец" if user_type == "guest" else "Заинтересованный человек"
    
    payload = {
        "branch": "contact_admin",
        "user_type": user_type,
        "message": user_message,
    }
    
    summary = f"Запрос к администратору ({user_type_label}): {user_message}"
    
    try:
        ticket = create_ticket(
            type_=TicketType.OTHER,
            guest_chat_id=str(message.from_user.id),
            guest_name=message.from_user.full_name,
            room_number=None,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        warning = "Вы отправили слишком много заявок. Пожалуйста, подождите."
        await message.answer(warning)
        await state.clear()
        return
    
    confirmation = f"Спасибо, ваша заявка #{ticket.id} принята. Администратор свяжется с вами в ближайшее время."
    await message.answer(confirmation)
    
    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)
    
    await state.clear()
