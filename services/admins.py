from __future__ import annotations

import logging

from aiogram import Bot
from sqlalchemy.orm import Session

from db.models import Ticket
from db.session import SessionLocal
from services.content import content_manager
from services.tickets import list_active_admins


logger = logging.getLogger(__name__)


async def notify_admins_about_ticket(bot: Bot, ticket: Ticket, summary: str) -> None:
    """Notify all active admins about the new ticket.

    If there are no admins configured, this function silently returns.
    """

    # DB operations here are synchronous; for MVP we accept short blocking calls.
    with SessionLocal() as session:  # type: Session
        admins = list_active_admins(session)

    if not admins:
        return

    text_template = content_manager.get_text("admin.new_ticket_notification")
    text = text_template.format(ticket_id=ticket.id, summary=summary)

    for admin in admins:
        try:
            await bot.send_message(chat_id=int(admin.telegram_id), text=text)
        except Exception as e:  # pragma: no cover - defensive logging
            logger.warning("Failed to notify admin %s: %s", admin.telegram_id, e)
