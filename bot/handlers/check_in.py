from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from db.models import Ticket, TicketType
from services.tickets import create_ticket
from services.admins import notify_admins_about_ticket
from bot.states import FlowState
from services.content import content_manager

router = Router()

@router.callback_query(F.data == "segment_pre_arrival")
async def welcome_pre_arrival(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FlowState.pre_arrival_menu)
    text = content_manager.get_text("menus.pre_arrival_title")
    from bot.keyboards.main_menu import build_pre_arrival_menu
    await callback.message.answer(text, reply_markup=build_pre_arrival_menu())
    await callback.answer()

@router.callback_query(F.data == "segment_in_house")
async def welcome_in_house(callback: CallbackQuery, state: FSMContext):
    # При переходе в "Я уже проживаю" присылаем Wi-Fi
    text = (
        "🏠 <b>Добро пожаловать в GORA!</b>\n\n"
        "🔑 <b>Wi-Fi в отеле:</b>\n"
        "Сеть: <code>GORA_HOTEL_GUEST</code>\n"
        "Пароль: <code>gora2024</code>\n\n"
        "☕ Завтраки проходят с 08:00 до 10:00 в ресторане на 1 этаже."
    )
    from bot.keyboards.main_menu import build_in_house_menu
    await state.set_state(FlowState.in_house_menu)
    await callback.message.answer(text, reply_markup=build_in_house_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "in_check_in")
async def start_check_in(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📸 <b>БЫСТРАЯ РЕГИСТРАЦИЯ</b>\n\nПожалуйста, пришлите фото вашего паспорта (главный разворот). Это ускорит ваше заселение!")
    await state.set_state("check_in_passport")
    await callback.answer()

@router.message(F.photo, F.state == "check_in_passport")
async def handle_passport(message: Message, state: FSMContext):
    ticket = create_ticket(
        type_=TicketType.CHECK_IN,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        initial_message="📸 Прислано фото паспорта для регистрации"
    )
    await message.answer(f"✅ Фото получено! Мы подготовим документы к вашему приходу. Номер вашей заявки: #{ticket.id}")
    await notify_admins_about_ticket(message.bot, ticket, f"📸 Новый паспорт для регистрации от {message.from_user.full_name}")
    await state.clear()
