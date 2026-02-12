from __future__ import annotations

from datetime import datetime, time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import (
    build_breakfast_after_deadline_menu,
    build_breakfast_confirm_menu,
    build_breakfast_entry_menu,
    build_contact_admin_type_menu,
)
from bot.states import FlowState
from bot.utils.reply_keyboards import build_role_reply_keyboard
from services.content import content_manager
from services.shelter_access import can_user_use_room_service


router = Router()


@router.callback_query(F.data == "back_to_in_house")
async def handle_back_to_in_house(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    await state.set_state(FlowState.in_house_menu)
    text = content_manager.get_text("menus.in_house_title")
    from bot.keyboards.main_menu import build_in_house_reply_keyboard
    await callback.message.answer(text)
    # Обновляем slash-меню
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_in_house_reply_keyboard()
    )


@router.callback_query(FlowState.in_house_menu)
async def handle_in_house_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    key = callback.data or ""

    if key == "in_room_service":
        if not await can_user_use_room_service(str(callback.from_user.id)):
            await state.clear()
            await callback.message.answer("нет доступа")
            return
        await state.set_state(FlowState.room_service_choosing_branch)
        text = content_manager.get_text("room_service.what_do_you_need")
        from bot.keyboards.main_menu import build_room_service_reply_keyboard
        await callback.message.answer(text)
        # Обновляем slash-меню
        await callback.message.answer(
            "Используйте кнопки ниже для выбора:",
            reply_markup=build_room_service_reply_keyboard()
        )
        return

    if key == "in_restaurant":
        # Handled by menu_order router, but update keyboard here
        from bot.keyboards.main_menu import build_menu_reply_keyboard
        await callback.message.answer(
            "Используйте кнопки ниже для выбора категории:",
            reply_markup=build_menu_reply_keyboard()
        )
        return

    if key == "in_additional_services":
        # Handled by additional_services router
        return

    if key == "in_admin":
        await state.set_state(FlowState.contact_admin_type)
        from bot.keyboards.main_menu import build_admin_contact_reply_keyboard
        await callback.message.answer("Выберите, кто вы:")
        # Обновляем slash-меню
        await callback.message.answer(
            "Используйте кнопки ниже для выбора:",
            reply_markup=build_admin_contact_reply_keyboard()
        )
        return

    if key == "in_guide":
        # Handled by guide router
        return

    if key == "in_weather":
        # Handled by weather router
        return

    if key == "in_sos":
        # Handled by sos router
        return

    if key == "in_loyalty":
        # Handled by loyalty router
        return

    mapping = {
        "in_walks_relax": "in_house.walks_relax",
        "in_recommendations": "in_house.recommendations",
    }

    text_key = mapping.get(key)
    if not text_key:
        await callback.answer()
        return

    text = content_manager.get_text(text_key)
    await callback.message.answer(text)
    await callback.message.answer(content_manager.get_text("menus.in_house_title"))


@router.callback_query(FlowState.breakfast_entry)
async def handle_breakfast_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    key = callback.data or ""

    if key == "breakfast_composition":
        text = content_manager.get_text("breakfast.composition")
        await callback.message.answer(text, parse_mode="HTML")
        await callback.message.answer(
            content_manager.get_text("breakfast.intro"),
            reply_markup=build_breakfast_entry_menu(),
        )
        return

    if key == "breakfast_order":
        await state.set_state(FlowState.breakfast_persons)
        await callback.message.answer(content_manager.get_text("breakfast.ask_persons"))


@router.message(FlowState.breakfast_persons)
async def handle_breakfast_persons(message: Message, state: FSMContext) -> None:
    raw = message.text or ""
    try:
        persons = int(raw)
    except ValueError:
        await message.answer(content_manager.get_text("breakfast.invalid_persons"))
        return

    if persons <= 0 or persons > 10:
        await message.answer(content_manager.get_text("breakfast.invalid_persons"))
        return

    price_per_person = 650
    total_price = persons * price_per_person

    await state.update_data(
        breakfast_persons=persons,
        breakfast_price_per_person=price_per_person,
        breakfast_total_price=total_price,
    )
    await state.set_state(FlowState.breakfast_confirm)

    template = content_manager.get_text("breakfast.confirm_prompt")
    text = template.format(persons=persons, price_per_person=price_per_person, total_price=total_price)
    await message.answer(text, reply_markup=build_breakfast_confirm_menu())


@router.callback_query(FlowState.breakfast_confirm)
async def handle_breakfast_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    from aiogram import Bot

    from db.models import TicketType
    from services.admins import notify_admins_about_ticket
    from services.tickets import TicketRateLimitExceededError, create_ticket

    key = callback.data or ""

    if key == "breakfast_confirm_no":
        await state.set_state(FlowState.in_house_menu)
        await callback.message.answer(content_manager.get_text("breakfast.order_cancelled"))
        return

    if key != "breakfast_confirm_yes":
        return

    data = await state.get_data()
    persons = data.get("breakfast_persons")
    price_per_person = data.get("breakfast_price_per_person", 650)
    total_price = data.get("breakfast_total_price", persons * price_per_person if persons else None)

    payload = {
        "branch": "breakfast",
        "persons": persons,
        "price_per_person": price_per_person,
        "total_price": total_price,
        "service_window": "09:00–10:00",
    }

    summary_template = content_manager.get_text("breakfast.ticket_summary")
    summary = summary_template.format(
        persons=persons,
        price_per_person=price_per_person,
        total_price=total_price,
    )

    try:
        ticket = create_ticket(
            type_=TicketType.BREAKFAST,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=None,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        warning = content_manager.get_text("tickets.rate_limited")
        await callback.message.answer(warning)
        await state.clear()
        await callback.answer()
        return

    confirmation_template = content_manager.get_text("breakfast.order_final_confirmation")
    confirmation = confirmation_template.format(
        ticket_id=ticket.id,
        persons=persons,
        total_price=total_price,
    )
    await callback.message.answer(confirmation, parse_mode="HTML")

    bot: Bot = callback.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    await state.clear()
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_role_reply_keyboard(str(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(FlowState.contact_admin_type)
async def handle_contact_admin_type(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle selection of user type when contacting admin."""
    await callback.answer()  # Acknowledge immediately
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
async def handle_contact_admin_message(message: Message, state: FSMContext) -> None:
    """Create ticket for admin contact request."""
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
        await message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=build_role_reply_keyboard(str(message.from_user.id))
        )
        return
    
    confirmation = f"Спасибо, ваша заявка #{ticket.id} принята. Администратор свяжется с вами в ближайшее время."
    await message.answer(confirmation)
    
    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)
    
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_role_reply_keyboard(str(message.from_user.id))
    )


@router.callback_query(FlowState.breakfast_after_deadline_choice)
async def handle_breakfast_after_deadline(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    from aiogram import Bot

    from db.models import TicketType
    from services.admins import notify_admins_about_ticket
    from services.tickets import TicketRateLimitExceededError, create_ticket

    key = callback.data or ""

    if key == "breakfast_cancel":
        await state.set_state(FlowState.in_house_menu)
        await callback.message.answer(content_manager.get_text("breakfast.after_deadline_cancelled"))
        return

    if key != "breakfast_contact_admin":
        return

    payload = {
        "branch": "breakfast_after_deadline",
    }

    summary_template = content_manager.get_text("breakfast.after_deadline_ticket_summary")
    summary = summary_template.format()

    try:
        ticket = create_ticket(
            type_=TicketType.ROOM_SERVICE,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=None,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        warning = content_manager.get_text("tickets.rate_limited")
        await callback.message.answer(warning)
        await state.clear()
        await callback.message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=build_role_reply_keyboard(str(callback.from_user.id))
        )
        await callback.answer()
        return

    confirmation = content_manager.get_text("tickets.created_confirmation").format(ticket_id=ticket.id)
    await callback.message.answer(confirmation)

    bot: Bot = callback.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    await state.clear()
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_role_reply_keyboard(str(callback.from_user.id))
    )
