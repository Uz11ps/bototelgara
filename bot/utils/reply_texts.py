from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


_REPLY_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "reply_buttons.ru.yml"

_DEFAULTS: dict[str, str] = {
    "main_home": "🏠 Главное меню",
    "main_pre_arrival": "Я планирую поездку",
    "main_in_house": "Я уже проживаю в отеле",
    "main_admin": "📞 Администратор",
    "main_room_service": "🛎 Рум-сервис",
    "staff_tasks": "🛠 Мои задачи",
    "staff_refresh": "🔄 Обновить задачи",
    "contact_guest": "🏠 Поселенец",
    "contact_interested": "❓ Заинтересованный человек",
    "room_technical": "🔧 Техническая проблема",
    "room_extra": "➕ Дополнительно в номер",
    "room_cleaning": "🧹 Уборка номера",
    "room_pillow": "🛏 Меню подушек",
    "room_other": "📝 Другое",
    "in_room_service": "🛎 Рум‑сервис",
    "in_breakfasts": "🍳 Завтраки",
    "in_guide": "🗺 Гид",
    "in_weather": "🌤 Погода",
    "in_sos": "🆘 SOS",
    "in_profile": "👤 Личный кабинет",
    "menu_breakfast": "🍳 Завтрак",
    "menu_lunch": "🍽 Обед",
    "menu_dinner": "🌙 Ужин",
    "menu_cart": "🛒 Корзина",
    "pre_book_room": "🏨 Забронировать номер",
    "pre_rooms_prices": "🛏 Номера и цены",
    "pre_about_hotel": "🌲 Об отеле",
    "pre_events": "🎉 Мероприятия",
    "pre_route": "📍 Как добраться",
    "pre_faq": "❓ Вопросы",
    "pre_restaurant": "🍽 Ресторан",
    "admin_all_tickets": "📋 Все активные заявки",
    "admin_pending_tickets": "⏳ Ожидающие решения",
    "admin_completed_today": "✅ Завершенные за сегодня",
    "admin_hotel_status": "🏨 Статус отеля",
    "admin_refresh": "🔄 Обновить",
    "admin_back_menu": "↩️ Назад в меню",
    "admin_reply": "💬 Ответить",
    "admin_complete": "✅ Отметить выполненной",
    "admin_decline": "❌ Отклонить",
    "admin_back_list": "↩️ Назад к списку",
    "inline_contact_guest": "🏠 Поселенец",
    "inline_contact_interested": "❓ Заинтересованный человек",
    "inline_menu_breakfast": "🍳 Завтрак",
    "inline_menu_lunch": "🍽 Обед",
    "inline_menu_dinner": "🌙 Ужин",
    "inline_menu_cart": "🛒 Корзина",
    "inline_back": "↩️ Назад",
    "inline_minus": "➖",
    "inline_plus": "➕",
    "inline_to_categories": "↩️ К категориям",
    "inline_checkout": "✅ Оформить заказ",
    "inline_clear_cart": "🗑 Очистить корзину",
    "inline_empty_cart": "Корзина пуста",
    "inline_confirm_order": "✅ Подтвердить заказ",
    "inline_cancel": "❌ Отменить",
    "inline_cleaning_not_needed": "🚫 Уборка не требуется",
    "inline_guest_booking_start": "✅ Указать данные проживания",
    "inline_guest_booking_later": "↩️ Позже",
    "staff_inline_refresh": "🔄 Обновить",
    "booking_upsell_breakfast": "🍳 Добавить завтрак (+650₽)",
    "booking_upsell_transfer": "🚗 Трансфер из аэропорта",
    "booking_upsell_skip": "⏩ Пропустить",
    "guide_nature": "🌲 Природа и Парки",
    "guide_cafes": "☕ Кафе и Рестораны",
    "guide_rent": "🚤 Активности и Прокат",
    "guide_back": "↩️ Назад",
    "guide_to_categories": "↩️ К категориям",
    "loyalty_history": "📜 История посещений",
    "loyalty_info": "🔄 Как потратить баллы?",
    "weather_back": "↩️ Назад",
    "dialog_close": "🔒 Закрыть диалог",
}


def _load() -> dict[str, Any]:
    if not _REPLY_PATH.exists():
        return {}
    with _REPLY_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data if isinstance(data, dict) else {}


def button_text(key: str) -> str:
    data = _load()
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return _DEFAULTS.get(key, key)
