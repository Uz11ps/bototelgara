from __future__ import annotations

from datetime import datetime, date, timedelta
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import FlowState
from services.shelter import get_shelter_client, ShelterAPIError
from services.content import content_manager

router = Router()

def build_calendar_keyboard(current_date: date, prefix: str) -> InlineKeyboardMarkup:
    """Simple calendar builder for date selection"""
    builder = InlineKeyboardBuilder()
    
    # Show next 14 days for simplicity
    for i in range(14):
        d = current_date + timedelta(days=i)
        builder.button(
            text=d.strftime("%d.%m"),
            callback_data=f"{prefix}:{d.isoformat()}"
        )
    
    builder.adjust(4)
    return builder.as_markup()

@router.callback_query(F.data == "pre_book_room")
async def start_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the booking process by asking for check-in date"""
    await state.set_state(FlowState.booking_check_in)
    await callback.message.answer(
        "Выберите дату заезда:",
        reply_markup=build_calendar_keyboard(date.today(), "checkin")
    )
    await callback.answer()

@router.callback_query(FlowState.booking_check_in, F.data.startswith("checkin:"))
async def select_check_in(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle check-in date selection and ask for check-out date"""
    check_in_str = callback.data.split(":")[1]
    check_in = date.fromisoformat(check_in_str)
    await state.update_data(check_in=check_in_str)
    
    await state.set_state(FlowState.booking_check_out)
    await callback.message.answer(
        f"Дата заезда: {check_in.strftime('%d.%m.%Y')}\nВыберите дату выезда:",
        reply_markup=build_calendar_keyboard(check_in + timedelta(days=1), "checkout")
    )
    await callback.answer()

@router.callback_query(FlowState.booking_check_out, F.data.startswith("checkout:"))
async def select_check_out(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle check-out date selection and ask for number of adults"""
    check_out_str = callback.data.split(":")[1]
    await state.update_data(check_out=check_out_str)
    
    await state.set_state(FlowState.booking_adults)
    builder = InlineKeyboardBuilder()
    for i in range(1, 5):
        builder.button(text=str(i), callback_data=f"adults:{i}")
    
    await callback.message.answer(
        "Сколько взрослых гостей?",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(FlowState.booking_adults, F.data.startswith("adults:"))
async def select_adults(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle adults selection and search for variants via Shelter API"""
    adults = int(callback.data.split(":")[1])
    await state.update_data(adults=adults)
    
    data = await state.get_data()
    check_in = date.fromisoformat(data["check_in"])
    check_out = date.fromisoformat(data["check_out"])
    
    await callback.message.answer("Ищу доступные номера...")
    
    try:
        shelter = get_shelter_client()
        variants = await shelter.get_variants(check_in, check_out, adults)
        
        if not variants:
            await callback.message.answer("К сожалению, на выбранные даты нет свободных номеров.")
            await state.clear()
            return
        
        await state.set_state(FlowState.booking_select_variant)
        for v in variants:
            builder = InlineKeyboardBuilder()
            builder.button(text="Забронировать", callback_data=f"variant:{v.signature_id}")
            
            text = (
                f"🏨 *{v.category_name}*\n"
                f"💰 Цена: {v.price} руб.\n"
                f"📋 Тариф: {v.rate_name}\n"
                f"👥 Вместимость: {v.capacity} чел.\n\n"
                f"{v.category_description[:200]}..."
            )
            
            await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
            
    except ShelterAPIError as e:
        await callback.message.answer(f"Ошибка при поиске номеров: {e.message or 'Неизвестная ошибка'}")
    
    await callback.answer()

@router.callback_query(FlowState.booking_select_variant, F.data.startswith("variant:"))
async def select_variant(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle variant selection and ask for upselling services"""
    signature_id = callback.data.split(":")[1]
    await state.update_data(signature_id=signature_id)
    
    await state.set_state("booking_upselling")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍳 Добавить завтрак (+650₽)", callback_data="upsell_breakfast")],
        [InlineKeyboardButton(text="🚗 Трансфер из аэропорта", callback_data="upsell_transfer")],
        [InlineKeyboardButton(text="⏩ Пропустить", callback_data="upsell_skip")]
    ])
    await callback.message.answer("✨ <b>Сделайте ваш отдых комфортнее!</b>\nЖелаете добавить дополнительные услуги?", reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("upsell_"))
async def handle_upselling(callback: CallbackQuery, state: FSMContext) -> None:
    upsell = callback.data.replace("upsell_", "")
    data = await state.get_data()
    upsells = data.get("upsells", [])
    if upsell != "skip":
        upsells.append(upsell)
        await state.update_data(upsells=upsells)
        await callback.answer(f"Добавлено: {upsell}", show_alert=True)
    
    await state.set_state(FlowState.booking_guest_name)
    await callback.message.answer("Введите ваше имя и фамилию:")
    await callback.answer()

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
    await callback.answer()

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel booking flow"""
    await state.clear()
    await callback.message.answer("Бронирование отменено.")
    await callback.answer()
