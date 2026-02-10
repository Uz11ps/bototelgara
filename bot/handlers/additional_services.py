from __future__ import annotations

import logging
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.states import FlowState
from services.content import content_manager
from services.tickets import create_ticket, TicketRateLimitExceededError
from db.models import TicketType
from services.admins import notify_admins_about_ticket
from aiogram import Bot

logger = logging.getLogger(__name__)
router = Router()

@router.callback_query(FlowState.in_house_menu, F.data == "in_additional_services")
async def start_additional_services(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    await state.set_state(FlowState.additional_services_menu)
    text = "🎯 <b>Дополнительные услуги</b>\n\nВыберите услугу для бронирования или получения информации:"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="🏄 Сап-борды", callback_data="service_sup")
    builder.button(text="⛵ Лодки и катера", callback_data="service_boats")
    builder.button(text="🧖‍♀️ Баня", callback_data="service_sauna")
    builder.button(text="🏠 Хаусботы", callback_data="service_houseboats")
    builder.button(text="🍖 Мангальные зоны", callback_data="service_grill")
    builder.button(text="↩️ Назад", callback_data="back_to_in_house")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(FlowState.additional_services_menu, F.data.startswith("service_"))
async def handle_service_selection(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    service_id = callback.data.replace("service_", "")
    
    services_info = {
        "sup": {
            "name": "Сап-борды",
            "text": "🏄 <b>Аренда сап-бордов</b>\n\n• Цена: 800 руб/час\n• В комплекте: жилет, весло\n• Инструктаж перед выходом\n\nХотите забронировать?",
        },
        "boats": {
            "name": "Лодки и катера",
            "text": "⛵ <b>Лодочные прогулки</b>\n\n• Моторные лодки: 1500 руб/час\n• Катера: 2500 руб/час\n• Прогулки со шкипером: от 5000 руб\n\nХотите забронировать?",
        },
        "sauna": {
            "name": "Баня",
            "text": "🧖‍♀️ <b>Баня на дровах</b>\n\n• Вместимость: до 12 человек\n• Стоимость: 3000 руб/сеанс (2 часа)\n• Включено: чай, дрова, простыни\n\nЗабронировать время?",
        },
        "houseboats": {
            "name": "Хаусботы",
            "text": "🏠 <b>Прогулки на хаусботах</b>\n\n• 3-часовая экскурсия по шхерам\n• Чай/кофе и закуски на борту\n• Стоимость: 2500 руб/чел\n\nОставить заявку?",
        },
        "grill": {
            "name": "Мангальные зоны",
            "text": "🍖 <b>Аренда мангальных зон</b>\n\n• Аренда зоны: 1000 руб/3 часа\n• Уголь, розжиг, решетки в наличии\n• Бронирование времени обязательно\n\nЗабронировать?",
        }
    }
    
    info = services_info.get(service_id)
    if not info:
        await callback.answer()
        return
        
    await state.update_data(current_service=info["name"])
    await state.set_state(FlowState.additional_services_booking)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Забронировать", callback_data="book_service_yes")
    builder.button(text="↩️ Назад", callback_data="in_additional_services")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(info["text"], reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(info["text"], reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(FlowState.additional_services_booking, F.data == "book_service_yes")
async def confirm_service_booking(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately to prevent freezing
    data = await state.get_data()
    service_name = data.get("current_service", "Дополнительная услуга")
    
    summary = f"Запрос на бронирование услуги: {service_name}"
    
    try:
        ticket = create_ticket(
            type_=TicketType.SERVICE_REQUEST,
            guest_chat_id=str(callback.from_user.id),
            guest_name=callback.from_user.full_name,
            room_number=None,
            initial_message=summary,
        )
    except TicketRateLimitExceededError:
        await callback.message.answer("Превышен лимит заявок. Пожалуйста, подождите.")
        await state.clear()
        return

    await callback.message.answer(
        f"✅ <b>Заявка принята!</b>\n\nУслуга: {service_name}\nНомер заявки: #{ticket.id}\n\nАдминистратор свяжется с вами для уточнения времени."
    )
    
    bot: Bot = callback.bot
    await notify_admins_about_ticket(bot, ticket, summary)
    
    await state.set_state(FlowState.in_house_menu)
    from bot.keyboards.main_menu import build_in_house_menu
    await callback.message.answer("Вернуться в меню:", reply_markup=build_in_house_menu())
