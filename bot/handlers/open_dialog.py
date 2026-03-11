from __future__ import annotations

from aiogram import F, Router
from aiogram.filters.state import StateFilter
from aiogram.types import Message

from db.models import TicketType
from db.session import SessionLocal
from services.admins import notify_admins_about_ticket
from services.guest_context import get_active_room_number
from services.tickets import (
    TicketRateLimitExceededError,
    append_guest_message_to_ticket,
    create_ticket,
    get_open_dialog_ticket_for_guest,
    is_user_admin,
)


router = Router()


@router.message(StateFilter(None), F.text.func(lambda text: not str(text).startswith("/")))
async def append_message_to_open_dialog(message: Message) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    user_id = str(message.from_user.id)
    with SessionLocal() as session:
        if is_user_admin(session, user_id):
            return
        ticket = get_open_dialog_ticket_for_guest(session, user_id)

    if ticket:
        updated_ticket = append_guest_message_to_ticket(ticket_id=ticket.id, content=text)
        if not updated_ticket:
            return
        summary = f"Новое сообщение в открытом диалоге #{updated_ticket.id}: {text}"
        bot = message.bot  # type: ignore[assignment]
        await notify_admins_about_ticket(bot, updated_ticket, summary)
        await message.answer(f"💬 Сообщение добавлено в диалог #{updated_ticket.id}. Администратор увидит его в этом же чате.")
        return

    # Fallback: если у гостя нет открытого диалога — создаём новый, чтобы сообщение не терялось
    room_number = get_active_room_number(user_id)
    try:
        ticket = create_ticket(
            type_=TicketType.PRE_ARRIVAL,
            guest_chat_id=user_id,
            guest_name=message.from_user.full_name,
            room_number=room_number,
            payload={"branch": "open_dialog_fallback", "message": text},
            initial_message=f"Новое обращение (диалог был закрыт): {text}",
            dialog_open=True,
            dialog_timeout_seconds=3600,
        )
    except TicketRateLimitExceededError:
        await message.answer(
            "Вы отправили слишком много сообщений. Пожалуйста, подождите или нажмите «📞 Администратор» в меню."
        )
        return

    summary = f"Новое обращение к администратору #{ticket.id}: {text}"
    bot = message.bot  # type: ignore[assignment]
    await notify_admins_about_ticket(bot, ticket, summary)
    await message.answer(
        f"💬 Создан новый диалог #{ticket.id}. Пишите сюда — администратор ответит в этом же чате."
    )
