from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from db.models import Ticket, TicketType, TicketStatus
from services.tickets import create_ticket
from services.admins import notify_admins_about_ticket

router = Router()

@router.callback_query(F.data == "in_sos")
async def start_sos(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🆘 <b>ЭКСТРЕННАЯ ПОМОЩЬ</b>\n\nОпишите вашу проблему максимально кратко. Администратор получит уведомление с высшим приоритетом!")
    await state.set_state("sos_message")
    await callback.answer()

@router.message(F.state == "sos_message")
async def handle_sos_message(message: Message, state: FSMContext):
    user_text = message.text or "Без описания"
    
    ticket = create_ticket(
        type_=TicketType.SOS,
        guest_chat_id=str(message.from_user.id),
        guest_name=message.from_user.full_name,
        initial_message=f"🚨 SOS: {user_text}"
    )
    
    await message.answer(f"✅ Ваша экстренная заявка #{ticket.id} отправлена! Администратор уже спешит на помощь.")
    
    # Уведомляем админов
    await notify_admins_about_ticket(message.bot, ticket, f"🚨 SOS от {message.from_user.full_name}: {user_text}")
    await state.clear()
