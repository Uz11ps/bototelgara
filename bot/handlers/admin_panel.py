"""
Admin panel handlers for managing tickets and viewing statistics.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import (
    build_admin_panel_menu,
    build_ticket_action_menu,
    build_ticket_list_keyboard,
)
from bot.states import FlowState
from db.models import TicketStatus, TicketType, TicketMessage, TicketMessageSender
from db.session import SessionLocal
from services.content import content_manager
from services.tickets import (
    get_all_active_tickets,
    get_pending_tickets,
    get_ticket_by_id,
    is_user_admin,
    update_ticket_status,
)


logger = logging.getLogger(__name__)
router = Router()


def format_ticket_summary(ticket) -> str:
    """Format ticket information for display."""
    type_names = {
        TicketType.ROOM_SERVICE: "Рум-сервис",
        TicketType.BREAKFAST: "Завтрак",
        TicketType.PRE_ARRIVAL: "До заезда",
        TicketType.OTHER: "Другое",
    }
    
    status_icons = {
        TicketStatus.NEW: "🆕",
        TicketStatus.PENDING_ADMIN: "⏳",
        TicketStatus.COMPLETED: "✅",
        TicketStatus.DECLINED: "❌",
        TicketStatus.CANCELLED: "🚫",
    }
    
    type_name = type_names.get(ticket.type, str(ticket.type))
    status_icon = status_icons.get(ticket.status, "")
    
    created = ticket.created_at.strftime("%d.%m.%Y %H:%M")
    guest_info = f"{ticket.guest_name}" if ticket.guest_name else f"ID: {ticket.guest_chat_id}"
    
    # Get initial message content
    message_preview = ""
    if ticket.messages:
        first_msg = ticket.messages[0].content
        message_preview = first_msg[:100] + "..." if len(first_msg) > 100 else first_msg
    
    return (
        f"{status_icon} <b>Заявка #{ticket.id}</b>\n"
        f"📝 Тип: {type_name}\n"
        f"👤 Гость: {guest_info}\n"
        f"🕐 Создана: {created}\n"
        f"💬 {message_preview}\n"
    )


@router.message(Command("admin", "panel"))
async def cmd_admin_panel(message: Message, state: FSMContext) -> None:
    """Show admin panel main menu."""
    # Clear any existing state first
    await state.clear()
    
    user_id = str(message.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await message.answer("❌ У вас нет доступа к админ-панели.")
            return
        
        pending_count = len(get_pending_tickets(session))
        all_count = len(get_all_active_tickets(session))
    
    welcome_text = (
        f"🔧 <b>Панель администратора</b>\n\n"
        f"📊 Активных заявок: {all_count}\n"
        f"⏳ Ожидают решения: {pending_count}\n\n"
        f"Выберите действие:"
    )
    
    await message.answer(welcome_text, reply_markup=build_admin_panel_menu(), parse_mode="HTML")


@router.callback_query(F.data == "admin_refresh")
async def admin_refresh(callback: CallbackQuery, state: FSMContext) -> None:
    """Refresh admin panel."""
    # Clear any reply state when returning to main menu
    current_state = await state.get_state()
    if current_state == FlowState.admin_reply:
        await state.clear()
    
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        pending_count = len(get_pending_tickets(session))
        all_count = len(get_all_active_tickets(session))
    
    welcome_text = (
        f"🔧 <b>Панель администратора</b>\n\n"
        f"📊 Активных заявок: {all_count}\n"
        f"⏳ Ожидают решения: {pending_count}\n\n"
        f"Выберите действие:"
    )
    
    # Only edit if content actually changed
    try:
        await callback.message.edit_text(welcome_text, reply_markup=build_admin_panel_menu(), parse_mode="HTML")
    except Exception:
        pass  # Ignore if message is the same
    
    await callback.answer("Обновлено")


@router.callback_query(F.data == "admin_all_tickets")
async def admin_all_tickets(callback: CallbackQuery) -> None:
    """Show all active tickets."""
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        tickets = get_all_active_tickets(session)
        logger.info(f"Admin {user_id} requested all tickets. Found: {len(tickets)}")
        
        if not tickets:
            text = "✅ Нет активных заявок"
            try:
                await callback.message.edit_text(text, reply_markup=build_admin_panel_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=build_admin_panel_menu())
            await callback.answer()
            return
        
        text = f"📋 <b>Все активные заявки ({len(tickets)})</b>\n\nВыберите заявку для просмотра:"
        keyboard = build_ticket_list_keyboard(tickets[:10])  # Show first 10 as buttons
        logger.info(f"Generated keyboard with {len(keyboard.inline_keyboard)} rows")
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "admin_pending_tickets")
async def admin_pending_tickets(callback: CallbackQuery, state: FSMContext) -> None:
    """Show pending tickets."""
    # Clear any reply state
    current_state = await state.get_state()
    if current_state == FlowState.admin_reply:
        await state.clear()
    
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        tickets = get_pending_tickets(session)
        logger.info(f"Admin {user_id} requested pending tickets. Found: {len(tickets)}")
        
        if not tickets:
            text = "✅ Нет заявок, ожидающих решения"
            try:
                await callback.message.edit_text(text, reply_markup=build_admin_panel_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=build_admin_panel_menu())
            await callback.answer()
            return
        
        text = f"⏳ <b>Заявки, ожидающие решения ({len(tickets)})</b>\n\nВыберите заявку:"
        keyboard = build_ticket_list_keyboard(tickets[:10])
        logger.info(f"Generated pending keyboard with {len(keyboard.inline_keyboard)} rows")
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "admin_completed_today")
async def admin_completed_today(callback: CallbackQuery, state: FSMContext) -> None:
    """Show completed tickets from today."""
    # Clear any reply state
    current_state = await state.get_state()
    if current_state == FlowState.admin_reply:
        await state.clear()
    
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        from db.models import Ticket
        
        tickets = (
            session.query(Ticket)
            .filter(
                Ticket.status == TicketStatus.COMPLETED,
                Ticket.updated_at >= today_start
            )
            .order_by(Ticket.updated_at.desc())
            .all()
        )
        
        if not tickets:
            text = "📭 Сегодня еще нет завершенных заявок"
            try:
                await callback.message.edit_text(text, reply_markup=build_admin_panel_menu())
            except Exception:
                await callback.message.answer(text, reply_markup=build_admin_panel_menu())
            await callback.answer()
            return
        
        text = f"✅ <b>Завершенные заявки за сегодня ({len(tickets)})</b>\n\nВыберите для просмотра:"
        keyboard = build_ticket_list_keyboard(tickets[:10])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await callback.answer()


@router.callback_query(F.data == "admin_hotel_status")
async def admin_hotel_status(callback: CallbackQuery, state: FSMContext) -> None:
    """Show hotel status from Shelter API."""
    # Clear any reply state
    current_state = await state.get_state()
    if current_state == FlowState.admin_reply:
        await state.clear()
    
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
    
    from services.shelter import get_shelter_client
    
    try:
        shelter = get_shelter_client()
        stats = await shelter.get_hotel_stats()
        
        status_text = (
            f"🏨 <b>Статус отеля GORA</b>\n\n"
            f"📊 <b>Номерной фонд:</b>\n"
            f"• Всего номеров: {stats.total_rooms}\n"
            f"• Занято: {stats.occupied_rooms}\n"
            f"• Свободно: {stats.available_rooms}\n\n"
            f"📈 <b>Загруженность:</b> {stats.occupancy_rate:.1%}\n\n"
            f"🕐 Обновлено: {stats.last_updated.strftime('%d.%m.%Y %H:%M')}"
        )
    except Exception as e:
        status_text = f"❌ Ошибка при получении статуса: {str(e)[:100]}"
    
    try:
        await callback.message.edit_text(status_text, reply_markup=build_admin_panel_menu(), parse_mode="HTML")
    except Exception:
        await callback.message.answer(status_text, reply_markup=build_admin_panel_menu(), parse_mode="HTML")
    
    await callback.answer()


@router.message(Command("reset"))
async def cmd_reset_state(message: Message, state: FSMContext) -> None:
    """Reset FSM state for admin."""
    user_id = str(message.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await message.answer("❌ У вас нет доступа.")
            return
    
    await state.clear()
    await message.answer("✅ Состояние сброшено. Вы можете продолжить работу.")


@router.message(Command("view_ticket"))
async def cmd_view_ticket(message: Message) -> None:
    """View detailed ticket information via command."""
    user_id = str(message.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await message.answer("❌ У вас нет доступа к просмотру заявок.")
            return
        
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID заявки: /view_ticket 123")
            return
        
        try:
            ticket_id = int(args[1])
        except ValueError:
            await message.answer("❌ Неверный формат ID заявки")
            return
        
        await render_ticket_details(message, ticket_id)


@router.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket_callback(callback: CallbackQuery) -> None:
    """View detailed ticket information via callback."""
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        ticket_id = int(callback.data.split("_")[-1])
        await render_ticket_details(callback.message, ticket_id, is_callback=True)
        await callback.answer()


async def render_ticket_details(message: Message, ticket_id: int, is_callback: bool = False) -> None:
    """Helper to render ticket details."""
    with SessionLocal() as session:
        ticket = get_ticket_by_id(session, ticket_id)
        
        if not ticket:
            text = f"❌ Заявка #{ticket_id} не найдена"
            if is_callback:
                await message.edit_text(text, reply_markup=build_admin_panel_menu())
            else:
                await message.answer(text)
            return
        
        # Format detailed view
        text = format_ticket_summary(ticket)
        text += "\n<b>📨 История сообщений:</b>\n\n"
        
        for msg in ticket.messages:
            sender_icon = {"GUEST": "👤", "ADMIN": "👨‍💼", "SYSTEM": "🤖"}.get(msg.sender.value, "")
            msg_time = msg.created_at.strftime("%d.%m %H:%M")
            text += f"{sender_icon} [{msg_time}] {msg.content}\n\n"
        
        if ticket.payload:
            text += "\n<b>📦 Дополнительная информация:</b>\n"
            for key, value in ticket.payload.items():
                text += f"• {key}: {value}\n"
    
    if is_callback:
        await message.edit_text(text, reply_markup=build_ticket_action_menu(ticket_id), parse_mode="HTML")
    else:
        await message.answer(text, reply_markup=build_ticket_action_menu(ticket_id), parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_complete_"))
async def admin_complete_ticket(callback: CallbackQuery) -> None:
    """Mark ticket as completed."""
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        ticket_id = int(callback.data.split("_")[-1])
        ticket = get_ticket_by_id(session, ticket_id)
        
        if not ticket:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        guest_chat_id = ticket.guest_chat_id
        
        if update_ticket_status(session, ticket_id, TicketStatus.COMPLETED):
            # Notify user
            notification_status = ""
            try:
                notification_text = content_manager.get_text("tickets.resolved").format(ticket_id=ticket_id)
                await callback.bot.send_message(chat_id=int(guest_chat_id), text=notification_text)
                notification_status = "\n\n✅ Уведомление отправлено гостю"
            except Exception as e:
                logger.error(f"Failed to notify user {guest_chat_id} about ticket {ticket_id} completion: {e}")
                notification_status = f"\n\n⚠️ Не удалось отправить уведомление гостю: {str(e)[:50]}"

            await callback.answer("✅ Заявка отмечена как выполненная")
            await callback.message.edit_text(
                f"✅ Заявка #{ticket_id} успешно завершена{notification_status}",
                reply_markup=build_admin_panel_menu()
            )
        else:
            await callback.answer("❌ Ошибка при обновлении заявки", show_alert=True)


@router.callback_query(F.data.startswith("admin_reply_"))
async def admin_reply_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the reply process for an admin."""
    user_id = str(callback.from_user.id)
    
    # Check if already in reply state
    current_state = await state.get_state()
    if current_state == FlowState.admin_reply:
        await callback.answer("⚠️ Вы уже отвечаете на заявку. Введите сообщение.", show_alert=True)
        return
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        ticket_id = int(callback.data.split("_")[-1])
        await state.update_data(reply_ticket_id=ticket_id)
        await state.set_state(FlowState.admin_reply)
        
        await callback.message.answer(
            f"✍️ <b>Ответ на заявку #{ticket_id}</b>\n\n"
            "Введите ваше сообщение для гостя:",
            parse_mode="HTML"
        )
        await callback.answer()


@router.message(FlowState.admin_reply)
async def admin_reply_process(message: Message, state: FSMContext) -> None:
    """Process the admin's reply message."""
    user_id = str(message.from_user.id)
    data = await state.get_data()
    ticket_id = data.get("reply_ticket_id")
    
    if not ticket_id:
        await message.answer("❌ Ошибка: ID заявки не найден.")
        await state.clear()
        return

    admin_content = message.text or ""
    if not admin_content:
        await message.answer("❌ Сообщение не может быть пустым.")
        return

    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await message.answer("❌ Нет доступа.")
            await state.clear()
            return
            
        ticket = get_ticket_by_id(session, ticket_id)
        if not ticket:
            await message.answer(f"❌ Заявка #{ticket_id} не найдена.")
            await state.clear()
            return
            
        # Create message in DB
        from uuid import uuid4
        new_msg = TicketMessage(
            ticket_id=ticket_id,
            sender=TicketMessageSender.ADMIN,
            content=admin_content,
            request_id=str(uuid4()),
            admin_telegram_id=str(message.from_user.id),
            admin_name=message.from_user.full_name
        )
        session.add(new_msg)
        session.commit()
        
        # Send to user
        try:
            admin_name = message.from_user.full_name or "Администратор"
            user_notification = (
                f"💬 Ответ от {admin_name} по заявке #{ticket_id}:\n\n"
                f"{admin_content}"
            )
            await message.bot.send_message(chat_id=int(ticket.guest_chat_id), text=user_notification)
            await message.answer(f"✅ Сообщение успешно отправлено гостю по заявке #{ticket_id}")
        except Exception as e:
            logger.error(f"Failed to send admin reply to user {ticket.guest_chat_id}: {e}")
            await message.answer(f"⚠️ Сообщение сохранено в базе, но не удалось отправить в Telegram гостю: {e}")

    await state.clear()
    # Show admin panel menu instead of re-rendering ticket details
    # This prevents accidental double replies
    await message.answer(
        "✅ Сообщение отправлено. Что дальше?",
        reply_markup=build_admin_panel_menu()
    )


@router.callback_query(F.data.startswith("admin_decline_"))
async def admin_decline_ticket(callback: CallbackQuery) -> None:
    """Decline ticket."""
    user_id = str(callback.from_user.id)
    
    with SessionLocal() as session:
        if not is_user_admin(session, user_id):
            await callback.answer("❌ Нет доступа", show_alert=True)
            return
        
        ticket_id = int(callback.data.split("_")[-1])
        ticket = get_ticket_by_id(session, ticket_id)
        
        if not ticket:
            await callback.answer("❌ Заявка не найдена", show_alert=True)
            return

        guest_chat_id = ticket.guest_chat_id
        
        if update_ticket_status(session, ticket_id, TicketStatus.DECLINED):
            # Notify user
            notification_status = ""
            try:
                notification_text = content_manager.get_text("tickets.declined").format(ticket_id=ticket_id)
                await callback.bot.send_message(chat_id=int(guest_chat_id), text=notification_text)
                notification_status = "\n\n✅ Уведомление отправлено гостю"
            except Exception as e:
                logger.error(f"Failed to notify user {guest_chat_id} about ticket {ticket_id} decline: {e}")
                notification_status = f"\n\n⚠️ Не удалось отправить уведомление гостю: {str(e)[:50]}"

            await callback.answer("❌ Заявка отклонена")
            await callback.message.edit_text(
                f"❌ Заявка #{ticket_id} отклонена{notification_status}",
                reply_markup=build_admin_panel_menu()
            )
        else:
            await callback.answer("❌ Ошибка при обновлении заявки", show_alert=True)
