"""
Handlers for user-admin dialog system.
This module handles messages and actions in active dialogs.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from bot.states import FlowState
from bot.utils.reply_texts import button_text
from db.models import TicketMessage, TicketMessageSender
from db.session import SessionLocal
from services.tickets import get_ticket_by_id, list_active_admins
from services.content import content_manager


logger = logging.getLogger(__name__)
router = Router()


@router.message(FlowState.user_dialog_active)
async def handle_user_dialog_message(message: Message, state: FSMContext) -> None:
    """Handle messages in active dialog with admin."""
    from aiogram import Bot
    
    data = await state.get_data()
    ticket_id = data.get("active_ticket_id")
    
    if not ticket_id:
        await message.answer("❌ Ошибка: диалог не найден.")
        await state.clear()
        return
    
    user_text = message.text or ""
    if not user_text:
        return
    
    # Save message to database
    with SessionLocal() as session:
        ticket = get_ticket_by_id(session, ticket_id)
        if not ticket:
            await message.answer(f"❌ Заявка #{ticket_id} не найдена.")
            await state.clear()
            return
        
        new_msg = TicketMessage(
            ticket_id=ticket_id,
            sender=TicketMessageSender.GUEST,
            content=user_text,
            request_id=str(uuid4())
        )
        session.add(new_msg)
        session.commit()
        
        # Notify admins
        admins = list_active_admins(session)
        
        bot: Bot = message.bot  # type: ignore[assignment]
        for admin in admins:
            try:
                admin_notification = (
                    f"💬 <b>Новое сообщение в заявке #{ticket_id}</b>\n\n"
                    f"Гость: {ticket.guest_name or ticket.guest_chat_id}\n\n"
                    f"{user_text}"
                )
                await bot.send_message(chat_id=int(admin.telegram_id), text=admin_notification, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Failed to notify admin {admin.telegram_id}: {e}")
    
    # Confirm to user
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text("dialog_close"), callback_data=f"close_dialog_{ticket_id}")]
    ])
    await message.answer("✅ Сообщение отправлено администратору. Можете продолжать писать.", reply_markup=keyboard)


@router.callback_query(F.data.startswith("close_dialog_"))
async def handle_close_dialog(callback: CallbackQuery, state: FSMContext) -> None:
    """Close active dialog with admin."""
    from bot.keyboards.main_menu import build_in_house_menu
    
    ticket_id = int(callback.data.split("_")[-1])
    
    # Get current state data to determine which menu to return to
    data = await state.get_data()
    
    # Add system message to ticket that dialog was closed
    with SessionLocal() as session:
        ticket = get_ticket_by_id(session, ticket_id)
        if ticket:
            system_msg = TicketMessage(
                ticket_id=ticket_id,
                sender=TicketMessageSender.SYSTEM,
                content="🔒 Пользователь закрыл диалог. Заявка ожидает ответа администратора.",
                request_id=str(uuid4())
            )
            session.add(system_msg)
            session.commit()
    
    await state.clear()
    
    text = (
        f"✅ <b>Диалог закрыт</b>\n\n"
        f"Ваша заявка #{ticket_id} остается активной. "
        f"Администратор свяжется с вами по необходимости."
    )
    
    await callback.message.edit_text(text, parse_mode="HTML")
    
    # Return to appropriate menu
    await state.set_state(FlowState.in_house_menu)
    await callback.message.answer(
        content_manager.get_text("menus.in_house_title"),
        reply_markup=build_in_house_menu()
    )
    await callback.answer()
