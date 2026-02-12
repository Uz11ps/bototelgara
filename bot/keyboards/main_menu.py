from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton

from services.content import content_manager
from bot.utils.reply_texts import button_text


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
        [InlineKeyboardButton(text=button_text("admin_all_tickets"), callback_data="admin_all_tickets")],
        [InlineKeyboardButton(text=button_text("admin_pending_tickets"), callback_data="admin_pending_tickets")],
        [InlineKeyboardButton(text=button_text("admin_completed_today"), callback_data="admin_completed_today")],
        [InlineKeyboardButton(text=button_text("admin_hotel_status"), callback_data="admin_hotel_status")],
        [InlineKeyboardButton(text=button_text("admin_refresh"), callback_data="admin_refresh")],
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
    
    buttons.append([InlineKeyboardButton(text=button_text("admin_back_menu"), callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_ticket_action_menu(ticket_id: int) -> InlineKeyboardMarkup:
    """Build action menu for a specific ticket."""
    buttons = [
        [InlineKeyboardButton(text=button_text("admin_reply"), callback_data=f"admin_reply_{ticket_id}")],
        [InlineKeyboardButton(text=button_text("admin_complete"), callback_data=f"admin_complete_{ticket_id}")],
        [InlineKeyboardButton(text=button_text("admin_decline"), callback_data=f"admin_decline_{ticket_id}")],
        [InlineKeyboardButton(text=button_text("admin_back_list"), callback_data="admin_all_tickets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_contact_admin_type_menu() -> InlineKeyboardMarkup:
    """Build menu for selecting user type when contacting admin."""
    buttons = [
        [InlineKeyboardButton(text=button_text("inline_contact_guest"), callback_data="contact_admin_guest")],
        [InlineKeyboardButton(text=button_text("inline_contact_interested"), callback_data="contact_admin_interested")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_menu_categories_keyboard() -> InlineKeyboardMarkup:
    """Build menu category selection keyboard."""
    buttons = [
        [InlineKeyboardButton(text=button_text("inline_menu_breakfast"), callback_data="menu_cat_breakfast")],
        [InlineKeyboardButton(text=button_text("inline_menu_lunch"), callback_data="menu_cat_lunch")],
        [InlineKeyboardButton(text=button_text("inline_menu_dinner"), callback_data="menu_cat_dinner")],
        [InlineKeyboardButton(text=button_text("inline_menu_cart"), callback_data="menu_view_cart")],
        [InlineKeyboardButton(text=button_text("inline_back"), callback_data="back_to_in_house")],
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
            InlineKeyboardButton(text=button_text("inline_minus"), callback_data=f"menu_item_minus_{item.id}"),
            InlineKeyboardButton(text=f"{qty}", callback_data="menu_noop"),
            InlineKeyboardButton(text=button_text("inline_plus"), callback_data=f"menu_item_plus_{item.id}"),
        ])
    
    # Bottom navigation
    buttons.append([InlineKeyboardButton(text=button_text("inline_menu_cart"), callback_data="menu_view_cart")])
    buttons.append([InlineKeyboardButton(text=button_text("inline_to_categories"), callback_data="menu_back_categories")])
    
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
        buttons.append([InlineKeyboardButton(text=button_text("inline_checkout"), callback_data="cart_checkout")])
        buttons.append([InlineKeyboardButton(text=button_text("inline_clear_cart"), callback_data="cart_clear")])
    else:
        buttons.append([InlineKeyboardButton(text=button_text("inline_empty_cart"), callback_data="cart_noop")])
    
    buttons.append([InlineKeyboardButton(text=button_text("admin_back_menu"), callback_data="menu_back_categories")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_order_confirm_keyboard() -> InlineKeyboardMarkup:
    """Build order confirmation keyboard."""
    buttons = [
        [InlineKeyboardButton(text=button_text("inline_confirm_order"), callback_data="order_confirm_yes")],
        [InlineKeyboardButton(text=button_text("inline_cancel"), callback_data="order_confirm_no")],
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
        [InlineKeyboardButton(text=button_text("inline_cleaning_not_needed"), callback_data="cleaning_not_needed")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_guest_booking_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for guest booking flow start."""
    buttons = [
        [InlineKeyboardButton(text=button_text("inline_guest_booking_start"), callback_data="guest_booking_start")],
        [InlineKeyboardButton(text=button_text("inline_guest_booking_later"), callback_data="back_to_in_house")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for main menu."""
    buttons = [
        [KeyboardButton(text=button_text("main_home"))],
        [KeyboardButton(text=button_text("main_pre_arrival"))],
        [KeyboardButton(text=button_text("main_in_house"))],
        [
            KeyboardButton(text=button_text("main_admin")),
            KeyboardButton(text=button_text("main_room_service"))
        ],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons, 
        resize_keyboard=True, 
        persistent=True,
        input_field_placeholder="Выберите действие..."
    )


def build_staff_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for staff members."""
    buttons = [
        [
            KeyboardButton(text=button_text("staff_tasks")),
            KeyboardButton(text=button_text("staff_refresh")),
        ],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите действие...",
    )


def build_admin_contact_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for admin contact section."""
    buttons = [
        [
            KeyboardButton(text=button_text("contact_guest")),
            KeyboardButton(text=button_text("contact_interested"))
        ],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите тип пользователя..."
    )


def build_room_service_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for room service section."""
    buttons = [
        [KeyboardButton(text=button_text("room_technical"))],
        [KeyboardButton(text=button_text("room_extra"))],
        [KeyboardButton(text=button_text("room_cleaning"))],
        [KeyboardButton(text=button_text("room_pillow"))],
        [KeyboardButton(text=button_text("room_other"))],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите тип услуги..."
    )


def build_in_house_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for in-house menu section."""
    buttons = [
        [
            KeyboardButton(text=button_text("in_room_service")),
            KeyboardButton(text=button_text("in_breakfasts"))
        ],
        [
            KeyboardButton(text=button_text("in_guide")),
            KeyboardButton(text=button_text("in_weather"))
        ],
        [
            KeyboardButton(text=button_text("in_sos")),
            KeyboardButton(text=button_text("in_profile"))
        ],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите раздел..."
    )


def build_pre_arrival_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for pre-arrival menu section."""
    buttons = [
        [KeyboardButton(text=button_text("pre_book_room"))],
        [KeyboardButton(text=button_text("pre_rooms_prices"))],
        [
            KeyboardButton(text=button_text("pre_about_hotel")),
            KeyboardButton(text=button_text("pre_events"))
        ],
        [
            KeyboardButton(text=button_text("pre_route")),
            KeyboardButton(text=button_text("pre_faq"))
        ],
        [
            KeyboardButton(text=button_text("pre_restaurant")),
            KeyboardButton(text=button_text("main_admin"))
        ],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите раздел..."
    )


def build_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for menu/restaurant section."""
    buttons = [
        [
            KeyboardButton(text=button_text("menu_breakfast")),
            KeyboardButton(text=button_text("menu_lunch")),
            KeyboardButton(text=button_text("menu_dinner"))
        ],
        [KeyboardButton(text=button_text("menu_cart"))],
        [KeyboardButton(text=button_text("main_home"))],
    ]
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Выберите категорию..."
    )
