from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

from services.content import content_manager


def build_segment_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    menu = content_manager.get_menu("segment_menu")
    for item in menu:
        if "web_app" in item:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=item["label"],
                        web_app=WebAppInfo(url=item["web_app"]),
                    )
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=item["label"],
                        callback_data=item["callback_data"],
                    )
                ]
            )
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
    



def _build_menu_from_key(menu_key: str) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    menu = content_manager.get_menu(menu_key)
    for item in menu:
        if "web_app" in item:
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=item["label"],
                        web_app=WebAppInfo(url=item["web_app"]),
                    )
                ]
            )
        else:
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


def build_menu_categories_keyboard() -> InlineKeyboardMarkup:
    """Build menu category selection keyboard."""
    buttons = [
        [InlineKeyboardButton(text="🍳 Завтрак", callback_data="menu_cat_breakfast")],
        [InlineKeyboardButton(text="🍽 Обед", callback_data="menu_cat_lunch")],
        [InlineKeyboardButton(text="🌙 Ужин", callback_data="menu_cat_dinner")],
        [InlineKeyboardButton(text="🛒 Корзина", callback_data="menu_view_cart")],
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_in_house")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_menu_items_keyboard(items: list, category: str, cart: dict = None) -> InlineKeyboardMarkup:
    """
    Build keyboard for menu items with quantity buttons.
    
    Args:
        items: List of MenuItem objects
        category: Current category for back button
        cart: Dict of {item_id: quantity} for current cart state
    """
    cart = cart or {}
    buttons = []
    
    for item in items:
        # Robust cart lookup (handle string/int keys)
        qty = cart.get(item.id) or cart.get(str(item.id), 0)

        # Row with item name and price
        item_text = f"{item.name} - {item.price}₽"
        if qty > 0:
            item_text = f"✅ {item.name} - {item.price}₽ (x{qty})"
        
        buttons.append([InlineKeyboardButton(text=item_text, callback_data=f"menu_item_info_{item.id}")])
        
        # Row with +/- buttons
        buttons.append([
            InlineKeyboardButton(text="➖", callback_data=f"menu_item_minus_{item.id}"),
            InlineKeyboardButton(text=f"{qty}", callback_data="menu_noop"),
            InlineKeyboardButton(text="➕", callback_data=f"menu_item_plus_{item.id}"),
        ])
    
    # Bottom navigation
    buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="menu_view_cart")])
    buttons.append([InlineKeyboardButton(text="↩️ К категориям", callback_data="menu_back_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_cart_keyboard(cart_items: list, total: float) -> InlineKeyboardMarkup:
    """
    Build cart review keyboard.
    
    Args:
        cart_items: List of tuples (MenuItem, quantity)
        total: Total price
    """
    buttons = []
    
    for item, qty in cart_items:
        buttons.append([
            InlineKeyboardButton(text=f"{item.name} x{qty} = {item.price * qty}₽", callback_data=f"cart_item_{item.id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"cart_remove_{item.id}"),
        ])
    
    if cart_items:
        buttons.append([InlineKeyboardButton(text=f"💰 Итого: {total}₽", callback_data="cart_noop")])
        buttons.append([InlineKeyboardButton(text="✅ Оформить заказ", callback_data="cart_checkout")])
        buttons.append([InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear")])
    else:
        buttons.append([InlineKeyboardButton(text="Корзина пуста", callback_data="cart_noop")])
    
    buttons.append([InlineKeyboardButton(text="↩️ Назад в меню", callback_data="menu_back_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build order confirmation keyboard."""
    buttons = [
        [InlineKeyboardButton(text="✅ Подтвердить заказ", callback_data="order_confirm_yes")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="order_confirm_no")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_cleaning_time_keyboard() -> InlineKeyboardMarkup:
    """Build cleaning time selection keyboard."""
    buttons = [
        [InlineKeyboardButton(text="12:00 - 13:00", callback_data="cleaning_12_13")],
        [InlineKeyboardButton(text="13:00 - 14:00", callback_data="cleaning_13_14")],
        [InlineKeyboardButton(text="14:00 - 15:00", callback_data="cleaning_14_15")],
        [InlineKeyboardButton(text="15:00 - 16:00", callback_data="cleaning_15_16")],
        [InlineKeyboardButton(text="16:00 - 17:00", callback_data="cleaning_16_17")],
        [InlineKeyboardButton(text="🚫 Уборка не требуется", callback_data="cleaning_not_needed")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_guest_booking_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for guest booking flow start."""
    buttons = [
        [InlineKeyboardButton(text="✅ Указать данные проживания", callback_data="guest_booking_start")],
        [InlineKeyboardButton(text="↩️ Позже", callback_data="back_to_in_house")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for main menu."""
    buttons = [
        [
            KeyboardButton(text="🏠 Главное меню"), 
            KeyboardButton(text="📱 Визуальное меню", web_app=WebAppInfo(url="https://gora.ru.net/menu"))
        ],
        [KeyboardButton(text="Я планирую поездку")],
        [KeyboardButton(text="Я уже проживаю в отеле")],
        [
            KeyboardButton(text="📞 Администратор"), 
            KeyboardButton(text="🛎 Рум-сервис")
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons, 
        resize_keyboard=True, 
        persistent=True,
        input_field_placeholder="Выберите действие..."
    )
