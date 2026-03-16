from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup

from bot.navigation import (
    VIEW_IN_HOUSE,
    VIEW_PRE_ARRIVAL,
    VIEW_SEGMENT,
    nav_back,
    nav_push,
    nav_reset,
)
from bot.states import FlowState
from services.content import content_manager


router = Router()


from datetime import datetime

from db.models import User
from db.session import SessionLocal


async def _show_segment_selection(message: Message, state: FSMContext) -> None:
    from bot.keyboards.main_menu import build_segment_reply_keyboard
    await state.set_state(FlowState.choosing_segment)
    await nav_reset(state, VIEW_SEGMENT)
    await message.answer(
        content_manager.get_text("menus.segment_choice_prompt"),
        reply_markup=build_segment_reply_keyboard()
    )


def _build_phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером телефона", request_contact=True)],
            [KeyboardButton(text="Пропустить")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def _get_reply_rows(menu_key: str, fallback_rows: list[list[str]]) -> list[list[str]]:
    try:
        raw = content_manager.get_menu(menu_key)
    except Exception:
        return fallback_rows

    rows: list[list[str]] = []
    for row in raw:
        if not isinstance(row, list):
            continue
        labels: list[str] = []
        for item in row:
            if isinstance(item, dict):
                label = str(item.get("label", "")).strip()
                if label:
                    labels.append(label)
        if labels:
            rows.append(labels)
    return rows or fallback_rows


def _label(rows: list[list[str]], row_idx: int, col_idx: int, default: str) -> str:
    try:
        return rows[row_idx][col_idx]
    except Exception:
        return default


def _labels_set(menu_key: str, fallback_rows: list[list[str]]) -> set[str]:
    rows = _get_reply_rows(menu_key, fallback_rows)
    return {item for row in rows for item in row}

def get_current_season() -> str:
    month = datetime.now().month
    if 3 <= month <= 5:
        return "spring"
    elif 6 <= month <= 8:
        return "summer"
    elif 9 <= month <= 11:
        return "autumn"
    else:
        return "winter"

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    from services.tickets import is_user_admin
    from bot.keyboards.main_menu import build_admin_panel_menu, build_main_reply_keyboard
    
    user_id = str(message.from_user.id)
    with SessionLocal() as session:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if user is None:
            user = User(
                telegram_id=user_id,
                full_name=message.from_user.full_name,
            )
            session.add(user)
        elif not user.full_name:
            user.full_name = message.from_user.full_name
        session.commit()
        missing_phone = not bool((user.phone or "").strip())
    
    # 1. Always send the main menu (Persistent Reply Keyboard) to ensure it's installed
    greeting = content_manager.get_text("greeting.start")
    season = get_current_season()
    seasonal_text = content_manager.get_text(f"seasons.{season}")

    await message.answer(
        f"{greeting}\n\n{seasonal_text}", 
        reply_markup=build_main_reply_keyboard()
    )

    if missing_phone:
        await state.update_data(phone_share_context="guest_onboarding")
        await message.answer(
            "📱 Поделитесь номером телефона, чтобы мы автоматически нашли ваше бронирование.",
            reply_markup=_build_phone_request_keyboard(),
        )
    else:
        await _show_segment_selection(message, state)
    
    # 2. Check if user is admin and show admin panel as a separate message
    with SessionLocal() as session:
        if is_user_admin(session, user_id):
            from services.tickets import get_pending_tickets, get_all_active_tickets
            pending_count = len(get_pending_tickets(session))
            all_count = len(get_all_active_tickets(session))
            
            admin_greeting = (
                f"👨‍💼 <b>Добро пожаловать в админ-панель отеля GORA</b>\n\n"
                f"📊 Активных заявок: {all_count}\n"
                f"⏳ Ожидают решения: {pending_count}\n\n"
                f"Выберите действие:"
            )
            
            await message.answer(admin_greeting, reply_markup=build_admin_panel_menu(), parse_mode="HTML")


@router.message(F.text == "Пропустить")
async def skip_phone_share(message: Message, state: FSMContext) -> None:
    await state.update_data(phone_share_context=None)
    await message.answer("Хорошо, вы сможете поделиться номером позже.")
    await _show_segment_selection(message, state)


@router.callback_query(F.data == "back_to_segment")
async def back_to_segment_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await _show_segment_selection(callback.message, state)


@router.callback_query(F.data == "nav:back")
async def nav_back_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    target = await nav_back(state)
    if target == VIEW_PRE_ARRIVAL:
        from bot.handlers.check_in import _handle_pre_arrival_logic
        await _handle_pre_arrival_logic(callback.message, state)
        return
    if target == VIEW_IN_HOUSE:
        from bot.handlers.check_in import _handle_in_house_logic
        await _handle_in_house_logic(callback.message, state, str(callback.from_user.id))
        return
    await _show_segment_selection(callback.message, state)


@router.message(
    F.text.func(
        lambda text: (text or "") in {
            _label(
                _get_reply_rows(
                    "reply_keyboards.segment",
                    [["Я планирую поездку"], ["Я уже проживаю в отеле"], ["Визуальное меню 📱"], ["🏠 Главное меню"]],
                ),
                3,
                0,
                "🏠 Главное меню",
            ),
            _label(
                _get_reply_rows(
                    "reply_keyboards.pre_arrival",
                    [
                        ["🏨 Забронировать номер"],
                        ["🌲 Об отеле", "🎉 Мероприятия"],
                        ["📍 Как добраться", "❓ Вопросы"],
                        ["🍽 Ресторан", "📞 Администратор"],
                        ["🏠 Главное меню"],
                    ],
                ),
                4,
                0,
                "🏠 Главное меню",
            ),
            _label(
                _get_reply_rows(
                    "reply_keyboards.room_service",
                    [["🛠 Технические проблемы"], ["🚰 Дополнительно в номер"], ["🧹 Уборка номера"], ["💤 Меню подушек"], ["📝 Другое"], ["🏠 Главное меню"]],
                ),
                5,
                0,
                "🏠 Главное меню",
            ),
        }
    )
)
async def reply_main_menu(message: Message, state: FSMContext) -> None:
    await _show_segment_selection(message, state)


@router.message(
    F.text.func(
        lambda text: (text or "") in {
            _label(
                _get_reply_rows(
                    "reply_keyboards.admin_contact",
                    [["🏠 Гость", "❓ Ищу отель"], ["🛎 Рум‑сервис", "🏠 Главное меню"]],
                ),
                0,
                0,
                "🏠 Гость",
            ),
            _label(
                _get_reply_rows(
                    "reply_keyboards.admin_contact",
                    [["🏠 Гость", "❓ Ищу отель"], ["🛎 Рум‑сервис", "🏠 Главное меню"]],
                ),
                0,
                1,
                "❓ Ищу отель",
            ),
        }
    )
)
async def reply_admin_type_selection(message: Message, state: FSMContext) -> None:
    """Handle admin type selection from reply keyboard."""
    admin_rows = _get_reply_rows(
        "reply_keyboards.admin_contact",
        [["🏠 Гость", "❓ Ищу отель"], ["🛎 Рум‑сервис", "🏠 Главное меню"]],
    )
    guest_label = _label(admin_rows, 0, 0, "🏠 Гость")
    user_type = "guest" if message.text == guest_label else "interested"
    await state.set_state(FlowState.contact_admin_type)
    await state.update_data(contact_admin_type=user_type)
    
    user_type_label = "Гость" if user_type == "guest" else "Ищу отель"
    await state.set_state(FlowState.contact_admin_message)
    await message.answer(f"Вы выбрали: {user_type_label}\n\nНапишите ваш вопрос или запрос:")


@router.message(
    F.text.func(
        lambda text: (text or "") in _labels_set(
            "reply_keyboards.room_service",
            [
                ["🛠 Технические проблемы"],
                ["🚰 Дополнительно в номер"],
                ["🧹 Уборка номера"],
                ["💤 Меню подушек"],
                ["📝 Другое"],
                ["🏠 Главное меню"],
            ],
        )
        or (text or "") in {"➕ Дополнительно в номер", "Другое"}
    )
)
async def reply_room_service_selection(message: Message, state: FSMContext) -> None:
    """Handle room service selection from reply keyboard."""
    from services.guest_context import get_active_room_number

    room_number = get_active_room_number(str(message.from_user.id))
    if not room_number:
        from bot.keyboards.main_menu import build_guest_booking_keyboard
        await message.answer(
            "🛎 Рум-сервис доступен только проживающим гостям.\n\nПожалуйста, укажите данные вашего проживания:",
            reply_markup=build_guest_booking_keyboard()
        )
        return
    
    rs_rows = _get_reply_rows(
        "reply_keyboards.room_service",
        [
            ["🛠 Технические проблемы"],
            ["🚰 Дополнительно в номер"],
            ["🧹 Уборка номера"],
            ["💤 Меню подушек"],
            ["📝 Другое"],
            ["🏠 Главное меню"],
        ],
    )
    mapping = {
        _label(rs_rows, 0, 0, "🛠 Технические проблемы"): "technical_problem",
        _label(rs_rows, 1, 0, "🚰 Дополнительно в номер"): "extra_to_room",
        "➕ Дополнительно в номер": "extra_to_room",
        _label(rs_rows, 2, 0, "🧹 Уборка номера"): "cleaning",
        _label(rs_rows, 3, 0, "💤 Меню подушек"): "pillow_menu",
        _label(rs_rows, 4, 0, "📝 Другое"): "other",
        "Другое": "other",
    }
    
    branch = mapping.get(message.text)
    if branch:
        await nav_push(state, "room_service")
        await state.update_data(service_branch=branch)
        if room_number:
            from bot.handlers.room_service import _continue_room_service_flow
            await state.update_data(room_number=room_number)
            await _continue_room_service_flow(message, state, branch)
            return
        await state.set_state(FlowState.room_service_room_number)
        await message.answer("🏠 Укажите номер вашей комнаты:")


@router.message(
    F.text.func(
        lambda text: (text or "") in _labels_set(
            "reply_keyboards.in_house",
            [
                ["🛎 Рум‑сервис"],
                ["🍳 Завтраки"],
                ["🗺 Гид по Сортавала"],
                ["🌤 Погода"],
                ["🎉 Актуальные мероприятия"],
                ["📷 Камеры"],
                ["📱 Визуальное меню"],
                ["📞 Администратор"],
                ["↩️ Назад"],
            ],
        )
        or (text or "") in {"🗺 Гид", "🆘 SOS", "👤 Личный кабинет"}
    )
)
async def reply_in_house_menu_selection(message: Message, state: FSMContext) -> None:
    """Handle in-house menu selection from reply keyboard."""
    from bot.handlers.in_house import _handle_in_room_service_logic

    class MockCallback:
        def __init__(self, message: Message, data: str, from_user):
            self.message = message
            self.data = data
            self.from_user = from_user

        async def answer(self):
            return

    in_house_rows = _get_reply_rows(
        "reply_keyboards.in_house",
        [
            ["🛎 Рум‑сервис"],
            ["🍳 Завтраки"],
            ["🗺 Гид по Сортавала"],
            ["🌤 Погода"],
            ["🎉 Актуальные мероприятия"],
            ["📷 Камеры"],
            ["📱 Визуальное меню"],
            ["📞 Администратор"],
            ["↩️ Назад"],
        ],
    )
    room_service_label = _label(in_house_rows, 0, 0, "🛎 Рум‑сервис")
    breakfast_label = _label(in_house_rows, 1, 0, "🍳 Завтраки")
    guide_label = _label(in_house_rows, 2, 0, "🗺 Гид по Сортавала")
    weather_label = _label(in_house_rows, 3, 0, "🌤 Погода")
    events_label = _label(in_house_rows, 4, 0, "🎉 Актуальные мероприятия")
    admin_label = _label(in_house_rows, 7, 0, "📞 Администратор")
    back_label = _label(in_house_rows, 8, 0, "↩️ Назад")

    if message.text == room_service_label:
        await _handle_in_room_service_logic(message, state, str(message.from_user.id))
    elif message.text == breakfast_label:
        from bot.handlers.menu_order import handle_menu_entry
        await state.set_state(FlowState.in_house_menu)
        await handle_menu_entry(MockCallback(message, "in_restaurant", message.from_user), state)
    elif message.text in {"🗺 Гид", guide_label}:
        from bot.handlers.guide import show_guide_categories
        await show_guide_categories(MockCallback(message, "in_guide", message.from_user))
    elif message.text == weather_label:
        from bot.handlers.weather import show_weather
        await show_weather(MockCallback(message, "in_weather", message.from_user))
    elif message.text == events_label:
        from bot.handlers.events import show_events
        await show_events(MockCallback(message, "pre_events_banquets", message.from_user), state)
    elif message.text == "🆘 SOS":
        from bot.handlers.sos import start_sos
        await start_sos(MockCallback(message, "in_sos", message.from_user), state)
    elif message.text == "👤 Личный кабинет":
        from bot.handlers.loyalty import show_loyalty
        await show_loyalty(MockCallback(message, "in_loyalty", message.from_user))
    elif message.text == admin_label:
        from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
        await _handle_pre_contact_admin_logic(message, state)
    elif message.text == back_label:
        await _show_segment_selection(message, state)


@router.message(F.text.in_({"🍳 Завтрак", "🍽 Обед", "🌙 Ужин", "🛒 Корзина"}))
async def reply_menu_selection(message: Message, state: FSMContext) -> None:
    """Handle menu category selection from reply keyboard."""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

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
    if message.text in {"🍳 Завтрак", "🍽 Обед", "🌙 Ужин"}:
        await message.answer(
            "Заказ завтрака, обеда и ужина теперь доступен только через визуальное меню.",
            reply_markup=visual_menu_kb,
        )
    elif message.text == "🛒 Корзина":
        await message.answer(
            "Корзина доступна в визуальном меню.",
            reply_markup=visual_menu_kb,
        )


@router.message(
    F.text.func(
        lambda text: (text or "") in {
            _label(
                _get_reply_rows(
                    "reply_keyboards.main",
                    [
                        ["🏨 Забронировать номер"],
                        ["🌲 Об отеле", "🎉 Мероприятия"],
                        ["📍 Как добраться", "❓ Вопросы"],
                        ["🍽 Ресторан", "📞 Администратор"],
                        ["👷‍♂️ Вход для сотрудников"],
                    ],
                ),
                0,
                0,
                "🏨 Забронировать номер",
            )
        }
    )
)
async def reply_book_room(message: Message, state: FSMContext) -> None:
    """Handle booking room from reply keyboard."""
    from bot.handlers.booking import _handle_booking_logic
    await _handle_booking_logic(message, state)

@router.message(
    F.text.func(
        lambda text: (text or "") in _labels_set(
            "reply_keyboards.pre_arrival",
            [
                ["🏨 Забронировать номер"],
                ["🌲 Об отеле", "🎉 Мероприятия"],
                ["📍 Как добраться", "❓ Вопросы"],
                ["🍽 Ресторан", "📞 Администратор (до заезда)"],
                ["🏠 Главное меню"],
            ],
        )
    )
)
async def reply_pre_arrival_selection(message: Message, state: FSMContext) -> None:
    """Handle pre-arrival menu selection from reply keyboard."""
    from bot.handlers.pre_arrival import (
        _handle_pre_how_to_get_logic,
        _handle_pre_faq_logic,
        _handle_pre_arrival_text_key_logic
    )

    pre_rows = _get_reply_rows(
        "reply_keyboards.pre_arrival",
        [
            ["🏨 Забронировать номер"],
            ["🌲 Об отеле", "🎉 Мероприятия"],
            ["📍 Как добраться", "❓ Вопросы"],
            ["🍽 Ресторан", "📞 Администратор (до заезда)"],
            ["🏠 Главное меню"],
        ],
    )
    how_to_get_label = _label(pre_rows, 2, 0, "📍 Как добраться")
    faq_label = _label(pre_rows, 2, 1, "❓ Вопросы")
    about_hotel_label = _label(pre_rows, 1, 0, "🌲 Об отеле")
    events_label = _label(pre_rows, 1, 1, "🎉 Мероприятия")
    restaurant_label = _label(pre_rows, 3, 0, "🍽 Ресторан")
    admin_label = _label(pre_rows, 3, 1, "📞 Администратор (до заезда)")

    if message.text == how_to_get_label:
        await _handle_pre_how_to_get_logic(message)
        return
    if message.text == faq_label:
        await _handle_pre_faq_logic(message)
        return
    if message.text == admin_label:
        from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
        await _handle_pre_contact_admin_logic(message, state, prefer_interested=True)
        return

    mapping = {
        about_hotel_label: "pre_arrival.about_hotel",
        restaurant_label: "pre_arrival.restaurant",
    }
    
    text_key = mapping.get(message.text)
    if text_key:
        await _handle_pre_arrival_text_key_logic(message, text_key)
        return

    if message.text == events_label:
        from bot.handlers.events import show_events
        class MockCallback:
            def __init__(self, message: Message, data: str, from_user):
                self.message = message
                self.data = data
                self.from_user = from_user

            async def answer(self):
                return
        await show_events(MockCallback(message, "pre_events_banquets", message.from_user), state)


@router.message(
    F.text.func(
        lambda text: (text or "") in {
            _label(
                _get_reply_rows(
                    "reply_keyboards.main",
                    [
                        ["🏨 Забронировать номер"],
                        ["🌲 Об отеле", "🎉 Мероприятия"],
                        ["📍 Как добраться", "❓ Вопросы"],
                        ["🍽 Ресторан", "📞 Администратор"],
                        ["👷‍♂️ Вход для сотрудников"],
                    ],
                ),
                3,
                1,
                "📞 Администратор",
            )
        }
    )
)
async def reply_admin_contact(message: Message, state: FSMContext) -> None:
    from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
    await _handle_pre_contact_admin_logic(message, state, prefer_interested=True)


@router.message(F.text == "📞 Связаться с администратором")
async def reply_admin_contact_legacy_text(message: Message, state: FSMContext) -> None:
    from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
    await _handle_pre_contact_admin_logic(message, state, prefer_interested=True)


@router.message(F.text == "📞 Администратор (до заезда)")
async def reply_admin_contact_pre_arrival_text(message: Message, state: FSMContext) -> None:
    from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
    await _handle_pre_contact_admin_logic(message, state, prefer_interested=True)


@router.message(
    F.text.func(
        lambda text: isinstance(text, str)
        and "администратор" in text.lower()
        and "сотрудник" not in text.lower()
    )
)
async def reply_admin_contact_fuzzy(message: Message, state: FSMContext) -> None:
    """Fallback for renamed admin button labels in guest menus."""
    from bot.handlers.pre_arrival import _handle_pre_contact_admin_logic
    await _handle_pre_contact_admin_logic(message, state, prefer_interested=True)


@router.message(F.text == "🛎 Рум-сервис")
async def reply_room_service(message: Message, state: FSMContext) -> None:
    from services.guest_context import get_active_room_number
    room_number = get_active_room_number(str(message.from_user.id))
    if not room_number:
        from bot.keyboards.main_menu import build_guest_booking_keyboard
        await message.answer(
            "🛎 Рум-сервис доступен только проживающим гостям.\n\nПожалуйста, укажите данные вашего проживания:",
            reply_markup=build_guest_booking_keyboard()
        )
        return
    from bot.keyboards.main_menu import build_room_service_menu, build_room_service_reply_keyboard
    await state.set_state(FlowState.room_service_choosing_branch)
    await nav_push(state, "room_service")
    await state.update_data(room_number=room_number)
    text = content_manager.get_text("room_service.what_do_you_need")
    await message.answer(text, reply_markup=build_room_service_menu())
    # Обновляем slash-меню
    await message.answer(
        "Используйте кнопки ниже для выбора:",
        reply_markup=build_room_service_reply_keyboard()
    )


# NOTE: segment_pre_arrival and segment_in_house callbacks are handled in check_in.py


@router.message(Command("reload_content"))
async def reload_content(message: Message) -> None:
    from db.session import SessionLocal
    from db.models import AdminUser

    user_id = str(message.from_user.id)

    with SessionLocal() as session:
        admin = (
            session.query(AdminUser)
            .filter(AdminUser.telegram_id == user_id, AdminUser.is_active == 1)
            .first()
        )

    if admin is None:
        text = content_manager.get_text("system.not_authorized")
        await message.answer(text)
        return

    content_manager.reload()
    text = content_manager.get_text("system.content_reloaded")
    await message.answer(text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Show available commands"""
    from db.session import SessionLocal
    from services.tickets import is_user_admin
    
    user_id = str(message.from_user.id)
    
    # Check if user is admin
    with SessionLocal() as session:
        is_admin = is_user_admin(session, user_id)
    
    if is_admin:
        help_text = (
            "📋 <b>Команды администратора:</b>\n\n"
            "<b>Управление заявками:</b>\n"
            "/admin или /panel - Админ-панель\n"
            "/view_ticket ID - Просмотр заявки\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n\n"
            "<b>Система:</b>\n"
            "/sheltertest - Проверка подключения к Shelter API\n"
            "/reload_content - Перезагрузить контент\n"
            "/help - Показать эту справку\n"
        )
    else:
        help_text = (
            "📋 <b>Доступные команды:</b>\n\n"
            "<b>Основные:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n\n"
            "<b>Информация об отеле:</b>\n"
            "/status или /hotelstatus - Статус загрузки отеля\n"
            "/rooms или /availability - Доступность номеров\n"
        )
    
    await message.answer(help_text, parse_mode="HTML")
