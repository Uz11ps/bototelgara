from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from services.content import content_manager


def build_segment_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    menu = content_manager.get_menu("segment_menu")
    for item in menu:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=item["label"],
                    callback_data=item["callback_data"],
                )
            ]
        )
    
    # Add Mini App button
    buttons.append([
        InlineKeyboardButton(
            text="📱 Визуальное меню (Mini App)",
            web_app=WebAppInfo(url="https://gora.ru.net")
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_menu_from_key(menu_key: str) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    menu = content_manager.get_menu(menu_key)
    for item in menu:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=item["label"],
                    callback_data=item["callback_data"],
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_pre_arrival_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("pre_arrival_menu")


def build_in_house_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("in_house_menu")


def build_room_service_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("room_service.branches")


def build_breakfast_entry_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("breakfast.entry_menu")


def build_breakfast_after_deadline_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("breakfast.after_deadline_menu")


def build_breakfast_confirm_menu() -> InlineKeyboardMarkup:
    return _build_menu_from_key("breakfast.confirm_menu")


def build_admin_panel_menu() -> InlineKeyboardMarkup:
    """Build admin panel main menu."""
    buttons = [
        [InlineKeyboardButton(text="📋 Все активные заявки", callback_data="admin_all_tickets")],
        [InlineKeyboardButton(text="⏳ Ожидающие решения", callback_data="admin_pending_tickets")],
        [InlineKeyboardButton(text="✅ Завершенные за сегодня", callback_data="admin_completed_today")],
        [InlineKeyboardButton(text="🏨 Статус отеля", callback_data="admin_hotel_status")],
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_refresh")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_ticket_list_keyboard(tickets: list, back_callback: str = "admin_refresh") -> InlineKeyboardMarkup:
    """Build keyboard for a list of tickets."""
    from db.models import TicketType
    import logging
    kb_logger = logging.getLogger(__name__)
    
    type_names = {
        TicketType.ROOM_SERVICE: "Рум",
        TicketType.BREAKFAST: "Завт",
        TicketType.PRE_ARRIVAL: "До заезда",
        TicketType.OTHER: "Другое",
    }
    
    buttons = []
    kb_logger.info(f"Building keyboard for {len(tickets)} tickets")
    for ticket in tickets:
        type_name = type_names.get(ticket.type, str(ticket.type))
        guest = ticket.guest_name or f"ID:{str(ticket.guest_chat_id)[:8]}"
        label = f"#{ticket.id} [{type_name}] {guest}"
        kb_logger.info(f"Adding button for ticket #{ticket.id}: {label}")
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"admin_view_ticket_{ticket.id}")])
    
    buttons.append([InlineKeyboardButton(text="↩️ Назад в меню", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_ticket_action_menu(ticket_id: int) -> InlineKeyboardMarkup:
    """Build action menu for a specific ticket."""
    buttons = [
        [InlineKeyboardButton(text="💬 Ответить", callback_data=f"admin_reply_{ticket_id}")],
        [InlineKeyboardButton(text="✅ Отметить выполненной", callback_data=f"admin_complete_{ticket_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_decline_{ticket_id}")],
        [InlineKeyboardButton(text="↩️ Назад к списку", callback_data="admin_all_tickets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_contact_admin_type_menu() -> InlineKeyboardMarkup:
    """Build menu for selecting user type when contacting admin."""
    buttons = [
        [InlineKeyboardButton(text="🏠 Поселенец", callback_data="contact_admin_guest")],
        [InlineKeyboardButton(text="❓ Заинтересованный человек", callback_data="contact_admin_interested")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
