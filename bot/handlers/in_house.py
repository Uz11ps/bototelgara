from __future__ import annotations

import html
from datetime import datetime, time

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import (
    build_breakfast_after_deadline_menu,
    build_breakfast_confirm_menu,
    build_breakfast_entry_menu,
    build_in_house_menu,
    build_room_service_menu,
    build_contact_admin_type_menu,
)
from bot.states import FlowState
from bot.navigation import VIEW_ROOM_SERVICE, nav_push
from services.content import content_manager
from services.guest_context import get_active_room_number


router = Router()

BREAKFAST_START_HOUR = 9
BREAKFAST_CUTOFF_HOUR = 17
BREAKFAST_CUTOFF_MINUTE = 45


def is_breakfast_order_available() -> bool:
    now = datetime.now().time()
    start = time(BREAKFAST_START_HOUR, 0)
    cutoff = time(BREAKFAST_CUTOFF_HOUR, BREAKFAST_CUTOFF_MINUTE)
    return start <= now <= cutoff


@router.callback_query(F.data == "back_to_in_house")
async def handle_back_to_in_house(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    await state.set_state(FlowState.in_house_menu)
    text = content_manager.get_text("menus.in_house_title")
    from bot.keyboards.main_menu import build_in_house_reply_keyboard
    try:
        await callback.message.edit_text(text, reply_markup=build_in_house_menu())
    except Exception:
        pass  # Ignore if message unchanged
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
        await _handle_in_room_service_logic(callback.message, state, str(callback.from_user.id))
        return

    if key == "in_restaurant":
        await _handle_in_restaurant_logic(callback.message)
        return

    if key == "in_additional_services":
        # Handled by additional_services router
        return

    if key == "in_admin":
        from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
        await _handle_pre_contact_admin_logic(callback.message, state)
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

    await _handle_in_house_text_key_logic(callback.message, text_key)


async def _handle_in_room_service_logic(message: Message, state: FSMContext, telegram_id: str):
    room_number = get_active_room_number(telegram_id)

    if not room_number:
        from bot.keyboards.main_menu import build_guest_booking_keyboard
        await message.answer(
            "🛎 Рум-сервис доступен только проживающим гостям.\n\nПожалуйста, укажите данные вашего проживания:",
            reply_markup=build_guest_booking_keyboard()
        )
        return

    await state.set_state(FlowState.room_service_choosing_branch)
    await nav_push(state, VIEW_ROOM_SERVICE)
    await state.update_data(room_number=room_number)
    text = content_manager.get_text("room_service.what_do_you_need")
    from bot.keyboards.main_menu import build_room_service_reply_keyboard, build_room_service_menu
    await message.answer(text, reply_markup=build_room_service_menu())
    # Обновляем slash-меню
    await message.answer(
        "Используйте кнопки ниже для выбора:",
        reply_markup=build_room_service_reply_keyboard()
    )


async def _handle_in_restaurant_logic(message: Message):
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    from bot.keyboards.main_menu import build_menu_reply_keyboard
    visual_menu_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть визуальное меню",
                    web_app=WebAppInfo(url="https://gora.ru.net/menu"),
                )
            ]
        ]
    )
    await message.answer(_build_breakfast_composition_from_menu(), parse_mode="HTML")
    await message.answer(
        "Заказ доступен через визуальное меню.",
        reply_markup=visual_menu_kb,
    )
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_menu_reply_keyboard()
    )


def _build_breakfast_composition_from_menu() -> str:
    from db.models import MenuItem, MenuCategory
    from db.session import SessionLocal

    with SessionLocal() as db:
        items = db.query(MenuItem).filter(
            MenuItem.is_available == True,
            (MenuItem.category == "breakfast") | (MenuItem.category_type == MenuCategory.BREAKFAST),
        ).order_by(MenuItem.id.asc()).all()

    if not items:
        return content_manager.get_text("breakfast.composition")

    lines: list[str] = ["🍳 <b>Актуальный состав завтраков</b>"]
    for item in items:
        name = html.escape(item.name or "")
        price = int(item.price) if item.price is not None else 0
        lines.append(f"\n• <b>{name}</b> — {price}₽")
        if item.description:
            lines.append(f"  {html.escape(item.description)}")
        composition_line = _format_item_composition(item.composition)
        if composition_line:
            lines.append(f"  <i>Состав:</i> {composition_line}")
    lines.append("\nЗаказ доступен через визуальное меню ниже.")
    return "\n".join(lines)


def _format_item_composition(composition: object) -> str:
    if isinstance(composition, list):
        parts: list[str] = []
        for comp in composition:
            if isinstance(comp, dict):
                comp_name = html.escape(str(comp.get("name", "")).strip())
                if not comp_name:
                    continue
                quantity = str(comp.get("quantity", "")).strip()
                unit = html.escape(str(comp.get("unit", "")).strip())
                if quantity and unit:
                    parts.append(f"{comp_name} ({quantity} {unit})")
                elif quantity:
                    parts.append(f"{comp_name} ({quantity})")
                else:
                    parts.append(comp_name)
            elif isinstance(comp, str):
                value = html.escape(comp.strip())
                if value:
                    parts.append(value)
        return ", ".join(parts)
    if isinstance(composition, str):
        return html.escape(composition.strip())
    return ""


async def _handle_in_house_text_key_logic(message: Message, text_key: str):
    text = content_manager.get_text(text_key)
    await message.answer(text)
    await message.answer(
        content_manager.get_text("menus.in_house_title"),
        reply_markup=build_in_house_menu(),
    )


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
        if not is_breakfast_order_available():
            await state.set_state(FlowState.breakfast_after_deadline_choice)
            await callback.message.answer(
                content_manager.get_text("breakfast.too_late"),
                reply_markup=build_breakfast_after_deadline_menu(),
            )
            return
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
        await callback.message.answer(
            content_manager.get_text("breakfast.order_cancelled"),
            reply_markup=build_in_house_menu(),
        )
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

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
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
async def handle_contact_admin_message(message: Message, state: FSMContext) -> None:
    """Create ticket for admin contact request."""
    from aiogram import Bot
    from db.models import TicketType
    from services.admins import notify_admins_about_ticket
    from services.tickets import TicketRateLimitExceededError, create_ticket
    
    user_message = message.text or ""
    data = await state.get_data()
    user_type = data.get("contact_admin_type", "guest")
    
    user_type_label = "Гость" if user_type == "guest" else "Ищу отель"
    room_number = get_active_room_number(str(message.from_user.id))
    
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
            room_number=room_number,
            payload=payload,
            initial_message=summary,
        )
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
    
    confirmation = f"Спасибо, ваша заявка #{ticket.id} принята. Администратор свяжется с вами в ближайшее время."
    await message.answer(confirmation)
    
    bot: Bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)
    
    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
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
        await callback.message.answer(
            content_manager.get_text("breakfast.after_deadline_cancelled"),
            reply_markup=build_in_house_menu(),
        )
        return

    if key != "breakfast_contact_admin":
        return

    payload = {
        "branch": "breakfast_after_deadline",
    }

    summary_template = content_manager.get_text("breakfast.after_deadline_ticket_summary")
    summary = summary_template.format()
    room_number = get_active_room_number(str(callback.from_user.id))

    try:
        ticket = create_ticket(
            type_=TicketType.ROOM_SERVICE,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=room_number,
            payload=payload,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        warning = content_manager.get_text("tickets.rate_limited")
        from bot.keyboards.main_menu import build_main_reply_keyboard
        await callback.message.answer(warning)
        await state.clear()
        await callback.message.answer(
            "Используйте кнопки ниже для навигации:",
            reply_markup=build_main_reply_keyboard()
        )
        await callback.answer()
        return

    confirmation = content_manager.get_text("tickets.created_confirmation").format(ticket_id=ticket.id)
    await callback.message.answer(confirmation)

    bot: Bot = callback.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)

    from bot.keyboards.main_menu import build_main_reply_keyboard
    await state.clear()
    await callback.message.answer(
        "Используйте кнопки ниже для навигации:",
        reply_markup=build_main_reply_keyboard()
    )
