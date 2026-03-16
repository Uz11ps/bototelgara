from __future__ import annotations

import json
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, ContentType
from aiogram.fsm.context import FSMContext

from db.models import TicketType
from services.tickets import create_ticket, TicketRateLimitExceededError, mark_order_guest_notified
from services.admins import notify_admins_about_ticket

logger = logging.getLogger(__name__)

router = Router()

@router.message(F.content_type == ContentType.WEB_APP_DATA)
async def handle_web_app_data(message: Message, state: FSMContext) -> None:
    """Handle data sent from Mini App (Web App)."""
    try:
        data = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("Ошибка обработки данных.")
        return

    logger.info(f"Received WebApp data: {data}")

    action = data.get("action")
    
    if action == "web_app_order":
        await process_web_app_order(message, data)
    elif action == "suggested_question":
        text = data.get("text")
        # Dispatch based on text
        if text == "Я планирую поездку":
            from bot.handlers.check_in import welcome_pre_arrival_text
            # We must set correct state since we are entering a flow
            await welcome_pre_arrival_text(message, state)
        elif text == "Я уже проживаю в отеле":
            from bot.handlers.check_in import welcome_in_house_text
            await welcome_in_house_text(message, state)
        elif text == "Визуальное меню 🗓️":
            # Just send the text message back to chat to confirm or trigger default handling
            await message.answer(f"Вы выбрали: {text}")
        else:
             await message.answer(f"Вы выбрали: {text}")
    else:
        # Fallback for old behavior (if any)
        await message.answer("Данные получены, спасибо!")


async def process_web_app_order(message: Message, data: dict) -> None:
    """Process an order from the Web App cart."""
    cart_items = data.get("cart", [])
    total = data.get("total", 0)
    
    if not cart_items:
        await message.answer("Корзина пуста.")
        return

    # User info
    user = message.from_user
    guest_name = user.full_name
    
    # Build summary
    summary = "🛒 <b>Новый заказ (Mini App)</b>\n\n"
    for item in cart_items:
        name = item.get("name", "Товар")
        qty = item.get("quantity", 1)
        price = item.get("price", 0)
        summary += f"• {name} x{qty} = {price * qty}₽\n"
    
    summary += f"\n<b>Итого: {total}₽</b>"
    
    # Create ticket
    from services.tickets import create_ticket
    try:
        ticket = create_ticket(
            type_=TicketType.MENU_ORDER,
            guest_chat_id=str(user.id),
            guest_name=guest_name,
            room_number="Web App", # We might want to ask for room number via bot flow later if needed, but for now specific "Web App" marker
            payload=data,
            initial_message=summary
        )
    except TicketRateLimitExceededError:
        await message.answer("Мы получили ваш заказ, но система перегружена. Пожалуйста, подождите подтверждения.")
        return

    # Notify User
    await message.answer(f"✅ <b>Заказ #{ticket.id} принят!</b>\n\n{summary}\n\nС вами свяжется администратор.", parse_mode="HTML")
    mark_order_guest_notified(ticket.id)

    # Notify Admins
    bot: Bot = message.bot
    await notify_admins_about_ticket(bot, ticket, summary)
