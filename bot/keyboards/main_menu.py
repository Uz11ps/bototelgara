from __future__ import annotations

from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import or_

from services.content import content_manager
from db.session import SessionLocal
from db.models import EventItem, MenuCategory, MenuCategorySetting, MenuItem


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


def build_segment_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for segment selection (Plan trip / Already in hotel)."""
    fallback_rows = [
        [{"label": "Я планирую поездку"}],
        [{"label": "Я уже проживаю в отеле"}],
        [{"label": "Визуальное меню 📱", "web_app": "https://gora.ru.net/menu"}],
        [{"label": "🏠 Главное меню"}, {"label": "👷‍♂️ Сотрудникам"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.segment",
        fallback_rows,
        "Выберите ваш статус..."
    )
    



def _build_menu_from_key(menu_key: str) -> InlineKeyboardMarkup:
    buttons: list[list[InlineKeyboardButton]] = []
    menu = content_manager.get_menu(menu_key)
    has_active_events = _has_active_events()
    for item in menu:
        callback_data = item.get("callback_data")
        if menu_key == "in_house_menu" and callback_data in {"in_sos", "in_loyalty"}:
            continue
        if not has_active_events and callback_data == "pre_events_banquets":
            continue
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
        [InlineKeyboardButton(text="🔒 Закрыть открытый диалог", callback_data=f"admin_close_dialog_{ticket_id}")],
        [InlineKeyboardButton(text="✅ Отметить выполненной", callback_data=f"admin_complete_{ticket_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_decline_{ticket_id}")],
        [InlineKeyboardButton(text="↩️ Назад к списку", callback_data="admin_all_tickets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_contact_admin_type_menu() -> InlineKeyboardMarkup:
    """Build menu for selecting user type when contacting admin."""
    buttons = [
        [InlineKeyboardButton(text="🏠 Гость", callback_data="contact_admin_guest")],
        [InlineKeyboardButton(text="❓ Ищу отель", callback_data="contact_admin_interested")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_menu_categories_keyboard() -> InlineKeyboardMarkup:
    """Build menu category selection keyboard."""
    labels = {
        "breakfast": "🍳 Завтрак",
        "lunch": "🍽 Обед",
        "dinner": "🌙 Ужин",
    }
    buttons: list[list[InlineKeyboardButton]] = []
    for category in ("breakfast", "lunch", "dinner"):
        if _is_category_visible_for_guest(category):
            buttons.append([InlineKeyboardButton(text=labels[category], callback_data=f"menu_cat_{category}")])
    buttons.append([InlineKeyboardButton(text="🛒 Корзина", callback_data="menu_view_cart")])
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_in_house")])
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
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back_categories")])
    
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
    
    buttons.append([InlineKeyboardButton(text="↩️ Назад", callback_data="menu_back_categories")])
    
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


def build_room_service_cleaning_slots_keyboard() -> InlineKeyboardMarkup:
    """Build cleaning slots for room-service requests."""
    buttons = [
        [InlineKeyboardButton(text="09:00 - 10:30", callback_data="rs_cleaning_slot:09:00-10:30")],
        [InlineKeyboardButton(text="10:30 - 12:00", callback_data="rs_cleaning_slot:10:30-12:00")],
        [InlineKeyboardButton(text="12:00 - 13:30", callback_data="rs_cleaning_slot:12:00-13:30")],
        [InlineKeyboardButton(text="13:30 - 15:00", callback_data="rs_cleaning_slot:13:30-15:00")],
        [InlineKeyboardButton(text="15:00 - 16:30", callback_data="rs_cleaning_slot:15:00-16:30")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_guest_booking_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for guest booking flow start."""
    buttons = [
        [InlineKeyboardButton(text="✅ Указать данные проживания", callback_data="guest_booking_start")],
        [InlineKeyboardButton(text="↩️ Позже", callback_data="back_to_in_house")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _build_reply_keyboard_from_menu_key(
    menu_key: str,
    fallback_rows: list[list[dict[str, str]]],
    input_field_placeholder: str,
) -> ReplyKeyboardMarkup:
    has_active_events = _has_active_events()
    try:
        rows = content_manager.get_menu(menu_key)
        if not isinstance(rows, list):
            rows = fallback_rows
    except Exception:
        rows = fallback_rows

    keyboard_rows: list[list[KeyboardButton]] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        buttons: list[KeyboardButton] = []
        for item in row:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            if not label:
                continue
            if not has_active_events and label in {"🎉 Мероприятия", "🎉 Актуальные мероприятия"}:
                continue
            if menu_key == "reply_keyboards.in_house" and ("SOS" in label or "Личный кабинет" in label):
                continue
            web_app_url = item.get("web_app")
            if isinstance(web_app_url, str) and web_app_url.strip():
                buttons.append(KeyboardButton(text=label, web_app=WebAppInfo(url=web_app_url)))
            else:
                buttons.append(KeyboardButton(text=label))
        if buttons:
            keyboard_rows.append(buttons)

    if not keyboard_rows:
        for row in fallback_rows:
            buttons: list[KeyboardButton] = []
            for item in row:
                label = item.get("label", "")
                if not has_active_events and label in {"🎉 Мероприятия", "🎉 Актуальные мероприятия"}:
                    continue
                web_app_url = item.get("web_app")
                if web_app_url:
                    buttons.append(KeyboardButton(text=label, web_app=WebAppInfo(url=web_app_url)))
                else:
                    buttons.append(KeyboardButton(text=label))
            if buttons:
                keyboard_rows.append(buttons)

    return ReplyKeyboardMarkup(
        keyboard=keyboard_rows,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder=input_field_placeholder
    )


def build_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for main menu."""
    fallback_rows = [
        [{"label": "🏨 Забронировать номер"}],
        [{"label": "🌲 Об отеле"}, {"label": "🎉 Мероприятия"}],
        [{"label": "📍 Как добраться"}, {"label": "❓ Вопросы"}],
        [{"label": "🍽 Ресторан"}, {"label": "📞 Администратор"}],
        [{"label": "👷‍♂️ Вход для сотрудников"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.main",
        fallback_rows,
        "Выберите раздел..."
    )


def build_admin_contact_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for admin contact section."""
    fallback_rows = [
        [{"label": "🏠 Гость"}, {"label": "❓ Ищу отель"}],
        [{"label": "🛎 Рум‑сервис"}, {"label": "🏠 Главное меню"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.admin_contact",
        fallback_rows,
        "Выберите тип пользователя..."
    )


def build_room_service_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for room service section."""
    fallback_rows = [
        [{"label": "🛠 Технические проблемы"}],
        [{"label": "🚰 Дополнительно в номер"}],
        [{"label": "🧹 Уборка номера"}],
        [{"label": "💤 Меню подушек"}],
        [{"label": "📝 Другое"}],
        [{"label": "🏠 Главное меню"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.room_service",
        fallback_rows,
        "Выберите тип услуги..."
    )


def build_in_house_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for in-house menu section."""
    fallback_rows = [
        [{"label": "🛎 Рум‑сервис"}],
        [{"label": "🍳 Завтраки"}],
        [{"label": "🗺 Гид по Сортавала"}],
        [{"label": "🌤 Погода"}],
        [{"label": "🎉 Актуальные мероприятия"}],
        [{"label": "📷 Камеры", "web_app": "https://gora.ru.net/menu?tab=cameras"}],
        [{"label": "📱 Визуальное меню", "web_app": "https://gora.ru.net/menu"}],
        [{"label": "📞 Администратор"}],
        [{"label": "↩️ Назад"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.in_house",
        fallback_rows,
        "Выберите раздел..."
    )


def build_pre_arrival_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for pre-arrival menu section."""
    fallback_rows = [
        [{"label": "🏨 Забронировать номер"}],
        [{"label": "🌲 Об отеле"}, {"label": "🎉 Мероприятия"}],
        [{"label": "📍 Как добраться"}, {"label": "❓ Вопросы"}],
        [{"label": "🍽 Ресторан"}, {"label": "📞 Администратор (до заезда)"}],
        [{"label": "🏠 Главное меню"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.pre_arrival",
        fallback_rows,
        "Выберите раздел..."
    )


def build_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build reply keyboard for menu/restaurant section."""
    fallback_rows = [
        [{"label": "📱 Визуальное меню", "web_app": "https://gora.ru.net/menu"}],
        [{"label": "🏠 Главное меню"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.menu",
        fallback_rows,
        "Выберите категорию..."
    )

def build_staff_reply_keyboard() -> ReplyKeyboardMarkup:
    """Build persistent reply keyboard for staff members."""
    fallback_rows = [
        [{"label": "📋 Мои задачи"}],
        [{"label": "🚪 Выйти из профиля сотрудника"}],
    ]
    return _build_reply_keyboard_from_menu_key(
        "reply_keyboards.staff",
        fallback_rows,
        "Панель сотрудника..."
    )


def _has_active_events() -> bool:
    now = datetime.utcnow()
    with SessionLocal() as db:
        return db.query(EventItem).filter(
            EventItem.is_active == True,
            or_(EventItem.publish_from.is_(None), EventItem.publish_from <= now),
            or_(EventItem.publish_until.is_(None), EventItem.publish_until >= now),
        ).first() is not None


def _is_category_visible_for_guest(category: str) -> bool:
    with SessionLocal() as db:
        setting = db.query(MenuCategorySetting).filter(
            MenuCategorySetting.category == MenuCategory(category).value
        ).first()
        enabled = bool(setting.is_enabled) if setting is not None else (category == "breakfast")
        if not enabled:
            return False
        has_items = db.query(MenuItem).filter(
            MenuItem.category == category,
            MenuItem.is_available == True
        ).first() is not None
        return has_items
