from __future__ import annotations

import json
from datetime import datetime, date, timedelta
from urllib.parse import urlencode
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import FlowState
from services.shelter import get_shelter_client, ShelterAPIError
from services.content import content_manager

router = Router()

def _build_children_age_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for age in range(0, 18):
        builder.button(text=str(age), callback_data=f"childage:{age}")
    builder.adjust(6)
    return builder.as_markup()


async def _send_booking_redirect(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    check_in = data["check_in"]
    check_out = data["check_out"]
    adults = int(data["adults"])
    children_ages = data.get("children_ages", []) or []
    children = len(children_ages)

    rooms_payload = json.dumps(
        [{"adults": adults, "ages": children_ages, "childrenAges": children_ages}],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    query = urlencode({
        # Keep both forms for better widget compatibility.
        "from": check_in,
        "to": check_out,
        "checkIn": check_in,
        "checkOut": check_out,
        "rooms": rooms_payload,
    })
    booking_url = f"https://gora-hotel.ru/book/?{query}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏨 Перейти к бронированию", url=booking_url)]
    ])
    await callback.message.answer(
        "Параметры выбраны. Откройте сайт, даты и количество гостей уже подставлены.",
        reply_markup=keyboard,
    )
    await callback.message.answer(
        "Итоговая стоимость рассчитывается на сайте по категории номера и возрасту детей."
    )

    if children:
        ages = ", ".join(str(age) for age in children_ages)
        await callback.message.answer(
            f"Состав гостей: взрослых — {adults}, детей — {children} (возраст: {ages})."
        )
    else:
        await callback.message.answer(f"Состав гостей: взрослых — {adults}, детей — 0.")
    await state.clear()


def build_calendar_keyboard(current_date: date, prefix: str) -> InlineKeyboardMarkup:
    """Simple calendar builder for date selection"""
    builder = InlineKeyboardBuilder()
    
    # Keep keyboard compact: ближайшие даты + отдельная кнопка для ручного ввода.
    for i in range(30):
        d = current_date + timedelta(days=i)
        builder.button(
            text=d.strftime("%d.%m"),
            callback_data=f"{prefix}:{d.isoformat()}"
        )
    builder.button(text="📅 Другая дата", callback_data=f"{prefix}_manual")
    builder.adjust(6)
    return builder.as_markup()

@router.callback_query(F.data == "pre_book_room")
async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the booking process by asking for check-in date"""
    await callback.answer()  # Acknowledge immediately
    await _handle_booking_logic(callback.message, state)


async def _handle_booking_logic(message: Message, state: FSMContext):
    from datetime import date
    await state.set_state(FlowState.booking_check_in)
    await message.answer(
        "Выберите дату заезда:",
        reply_markup=build_calendar_keyboard(date.today(), "checkin")
    )


def _parse_manual_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    for fmt in ("%d.%m.%y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


@router.callback_query(FlowState.booking_check_in, F.data == "checkin_manual")
async def ask_manual_check_in(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FlowState.booking_manual_check_in)
    await callback.message.answer("Введите дату заезда в формате ДД.ММ.ГГ (например, 25.03.26):")


@router.message(FlowState.booking_manual_check_in)
async def handle_manual_check_in(message: Message, state: FSMContext) -> None:
    check_in = _parse_manual_date(message.text or "")
    if not check_in:
        await message.answer("Неверный формат даты. Введите дату заезда в формате ДД.ММ.ГГ.")
        return
    if check_in < date.today():
        await message.answer("Дата заезда не может быть в прошлом. Укажите корректную дату.")
        return

    await state.update_data(check_in=check_in.isoformat())
    await state.set_state(FlowState.booking_check_out)
    await message.answer(
        f"Дата заезда: {check_in.strftime('%d.%m.%Y')}\nВыберите дату выезда:",
        reply_markup=build_calendar_keyboard(check_in + timedelta(days=1), "checkout")
    )

@router.callback_query(FlowState.booking_check_in, F.data.startswith("checkin:"))
async def select_check_in(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle check-in date selection and ask for check-out date"""
    await callback.answer()  # Acknowledge immediately
    check_in_str = callback.data.split(":")[1]
    check_in = date.fromisoformat(check_in_str)
    await state.update_data(check_in=check_in_str)
    
    await state.set_state(FlowState.booking_check_out)
    await callback.message.answer(
        f"Дата заезда: {check_in.strftime('%d.%m.%Y')}\nВыберите дату выезда:",
        reply_markup=build_calendar_keyboard(check_in + timedelta(days=1), "checkout")
    )

@router.callback_query(FlowState.booking_check_out, F.data.startswith("checkout:"))
async def select_check_out(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle check-out date selection and ask for number of adults"""
    await callback.answer()  # Acknowledge immediately
    check_out_str = callback.data.split(":")[1]
    data = await state.get_data()
    check_in = date.fromisoformat(data["check_in"])
    check_out_date = date.fromisoformat(check_out_str)
    if check_out_date <= check_in:
        await callback.message.answer("Дата выезда должна быть позже даты заезда.")
        return
    await state.update_data(check_out=check_out_str)
    
    await state.set_state(FlowState.booking_adults)
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.button(text=str(i), callback_data=f"adults:{i}")
    
    await callback.message.answer(
        "Сколько взрослых гостей?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(FlowState.booking_check_out, F.data == "checkout_manual")
async def ask_manual_check_out(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(FlowState.booking_manual_check_out)
    await callback.message.answer("Введите дату выезда в формате ДД.ММ.ГГ (например, 28.03.26):")


@router.message(FlowState.booking_manual_check_out)
async def handle_manual_check_out(message: Message, state: FSMContext) -> None:
    check_out = _parse_manual_date(message.text or "")
    if not check_out:
        await message.answer("Неверный формат даты. Введите дату выезда в формате ДД.ММ.ГГ.")
        return

    data = await state.get_data()
    check_in = date.fromisoformat(data["check_in"])
    if check_out <= check_in:
        await message.answer("Дата выезда должна быть позже даты заезда.")
        return

    await state.update_data(check_out=check_out.isoformat())
    await state.set_state(FlowState.booking_adults)
    builder = InlineKeyboardBuilder()
    for i in range(1, 7):
        builder.button(text=str(i), callback_data=f"adults:{i}")
    await message.answer(
        "Сколько взрослых гостей?",
        reply_markup=builder.as_markup()
    )

@router.callback_query(FlowState.booking_adults, F.data.startswith("adults:"))
async def select_adults(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle adults selection and ask children count."""
    await callback.answer()  # Acknowledge immediately
    adults = int(callback.data.split(":")[1])
    await state.update_data(adults=adults)

    await state.set_state(FlowState.booking_children)
    builder = InlineKeyboardBuilder()
    for i in range(0, 7):
        builder.button(text=str(i), callback_data=f"children:{i}")
    await callback.message.answer(
        "Сколько детей?",
        reply_markup=builder.as_markup()
    )


@router.callback_query(FlowState.booking_children, F.data.startswith("children:"))
async def select_children(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle children selection and redirect to site booking with prefilled params."""
    await callback.answer()
    children = int(callback.data.split(":")[1])
    await state.update_data(children=children, children_ages=[])

    if children == 0:
        await _send_booking_redirect(callback, state)
        return

    await state.set_state(FlowState.booking_child_age)
    await callback.message.answer(
        f"Укажите возраст ребенка 1 из {children}:",
        reply_markup=_build_children_age_keyboard()
    )


@router.callback_query(FlowState.booking_child_age, F.data.startswith("childage:"))
async def select_child_age(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    age = int(callback.data.split(":")[1])
    data = await state.get_data()
    children_count = int(data.get("children", 0))
    children_ages = list(data.get("children_ages", []) or [])
    children_ages.append(age)
    await state.update_data(children_ages=children_ages)

    if len(children_ages) < children_count:
        await callback.message.answer(
            f"Укажите возраст ребенка {len(children_ages) + 1} из {children_count}:",
            reply_markup=_build_children_age_keyboard()
        )
        return

    await _send_booking_redirect(callback, state)

@router.callback_query(FlowState.booking_select_variant, F.data.startswith("variant:"))
async def select_variant(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle variant selection and ask for upselling services"""
    await callback.answer()  # Acknowledge immediately
    signature_id = callback.data.split(":")[1]
    await state.update_data(signature_id=signature_id)
    
    await state.set_state("booking_upselling")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Добавить завтрак (+650₽)", callback_data="upsell_breakfast")],
        [InlineKeyboardButton(text="🚗 Трансфер из аэропорта", callback_data="upsell_transfer")],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data="upsell_skip")]
    ])
    await callback.message.answer("✨ <b>Сделайте ваш отдых комфортнее!</b>\nЖелаете добавить дополнительные услуги?", reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith("upsell_"))
async def handle_upselling(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()  # Acknowledge immediately
    upsell = callback.data.replace("upsell_", "")
    data = await state.get_data()
    upsells = data.get("upsells", [])
    if upsell != "skip":
        upsells.append(upsell)
        await state.update_data(upsells=upsells)
    
    await state.set_state(FlowState.booking_guest_name)
    await callback.message.answer("Введите ваше имя и фамилию:")

@router.message(FlowState.booking_guest_name)
async def enter_guest_name(message: Message, state: FSMContext) -> None:
    """Handle guest name and ask for phone"""
    await state.update_data(guest_name=message.text)
    await state.set_state(FlowState.booking_guest_phone)
    await message.answer("Введите ваш номер телефона:")

@router.message(FlowState.booking_guest_phone)
async def enter_guest_phone(message: Message, state: FSMContext) -> None:
    """Handle guest phone and ask for email"""
    await state.update_data(guest_phone=message.text)
    await state.set_state(FlowState.booking_guest_email)
    await message.answer("Введите ваш email:")

@router.message(FlowState.booking_guest_email)
async def enter_guest_email(message: Message, state: FSMContext) -> None:
    """Handle guest email and show confirmation"""
    await state.update_data(guest_email=message.text)
    data = await state.get_data()
    
    # In a real app, we would fetch variant details again or store them
    text = (
        f"📝 *Проверьте данные бронирования:*\n\n"
        f"📅 Заезд: {data['check_in']}\n"
        f"📅 Выезд: {data['check_out']}\n"
        f"👥 Гостей: {data['adults']}\n"
        f"👤 Имя: {data['guest_name']}\n"
        f"📞 Тел: {data['guest_phone']}\n"
        f"📧 Email: {data['guest_email']}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    
    await state.set_state(FlowState.booking_confirm)
    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@router.callback_query(FlowState.booking_confirm, F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Finalize booking via Shelter API"""
    await callback.answer()  # Acknowledge immediately
    data = await state.get_data()
    
    customer = {
        "firstName": data["guest_name"].split()[0] if " " in data["guest_name"] else data["guest_name"],
        "lastName": data["guest_name"].split()[1] if " " in data["guest_name"] else "",
        "phone": data["guest_phone"],
        "email": data["guest_email"]
    }
    
    guests = [{"firstName": customer["firstName"], "lastName": customer["lastName"]}]
    
    await callback.message.answer("Оформляю бронирование...")
    
    try:
        shelter = get_shelter_client()
        # For MVP, we use paymentTypeId=1 (usually "at hotel" or similar)
        # In a real app, we should fetch payment options first
        result = await shelter.put_order(
            signature_id=data["signature_id"],
            payment_type_id=1, 
            customer=customer,
            guests=guests,
            comment="Забронировано через Telegram Bot"
        )
        
        order_number = result.get("orderNumber", "N/A")
        await callback.message.answer(
            f"🎉 *Бронирование успешно оформлено!*\n\n"
            f"Номер вашего заказа: `{order_number}`\n"
            f"Мы отправили подтверждение на ваш email.",
            parse_mode="Markdown"
        )
        
    except ShelterAPIError as e:
        await callback.message.answer(f"Ошибка при создании бронирования: {e.message or 'Неизвестная ошибка'}")
    
    await state.clear()

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel booking flow"""
    await callback.answer()  # Acknowledge immediately
    await state.clear()
    await callback.message.answer("Бронирование отменено.")
