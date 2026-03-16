from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from db.models import AdminUser, Ticket, TicketMessage, TicketMessageSender, TicketStatus, TicketType
from db.session import SessionLocal


logger = logging.getLogger(__name__)

RATE_LIMIT_MAX_TICKETS = 3
RATE_LIMIT_WINDOW_SECONDS = 60
DIALOG_TIMEOUT_SECONDS_DEFAULT = 3600


class TicketRateLimitExceededError(Exception):
    """Raised when a user creates too many tickets in a short period of time."""


def create_ticket(
    *,
    type_: TicketType,
    guest_chat_id: str,
    guest_name: str | None,
    room_number: str | None,
    payload: dict[str, Any] | None,
    initial_message: str,
    rate_limit: bool = True,
    dialog_open: bool = False,
    dialog_timeout_seconds: int | None = None,
) -> Ticket:
    """Create a ticket and an initial guest message.

    This function is synchronous and uses a short-lived DB session.
    """

    from uuid import uuid4

    request_id = str(uuid4())

    with SessionLocal() as session:  # type: Session
        if rate_limit:
            window_start = datetime.utcnow() - timedelta(seconds=RATE_LIMIT_WINDOW_SECONDS)
            recent_count = (
                session.query(Ticket)
                .filter(
                    Ticket.guest_chat_id == guest_chat_id,
                    Ticket.created_at >= window_start,
                )
                .count()
            )
            if recent_count >= RATE_LIMIT_MAX_TICKETS:
                logger.warning(
                    "Rate limit exceeded for user %s: %s tickets in the last %s seconds",
                    guest_chat_id,
                    recent_count,
                    RATE_LIMIT_WINDOW_SECONDS,
                )
                raise TicketRateLimitExceededError("Too many tickets created in a short period of time")

        ticket = Ticket(
            type=type_,
            status=TicketStatus.PENDING_ADMIN,
            guest_chat_id=guest_chat_id,
            guest_name=guest_name,
            room_number=room_number,
            payload=payload,
            request_id=request_id,
            dialog_open=dialog_open,
            dialog_expires_at=(
                datetime.utcnow() + timedelta(seconds=(dialog_timeout_seconds or DIALOG_TIMEOUT_SECONDS_DEFAULT))
                if dialog_open
                else None
            ),
            dialog_last_activity_at=datetime.utcnow() if dialog_open else None,
        )
        session.add(ticket)
        session.flush()

        message = TicketMessage(
            ticket_id=ticket.id,
            sender=TicketMessageSender.GUEST,
            content=initial_message,
            request_id=request_id,
        )
        session.add(message)
        session.commit()
        session.refresh(ticket)
        logger.info("Created ticket id=%s type=%s request_id=%s", ticket.id, ticket.type, ticket.request_id)
        return ticket


def get_open_dialog_ticket_for_guest(session: Session, guest_chat_id: str) -> Ticket | None:
    now = datetime.utcnow()
    return (
        session.query(Ticket)
        .filter(
            Ticket.guest_chat_id == guest_chat_id,
            Ticket.dialog_open == True,
            Ticket.status.in_([TicketStatus.NEW, TicketStatus.PENDING_ADMIN]),
            or_(Ticket.dialog_expires_at.is_(None), Ticket.dialog_expires_at > now),
        )
        .order_by(Ticket.updated_at.desc())
        .first()
    )


def append_guest_message_to_ticket(
    *,
    ticket_id: int,
    content: str,
    dialog_timeout_seconds: int = DIALOG_TIMEOUT_SECONDS_DEFAULT,
) -> Ticket | None:
    with SessionLocal() as session:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return None
        message = TicketMessage(
            ticket_id=ticket.id,
            sender=TicketMessageSender.GUEST,
            content=content,
            request_id=ticket.request_id,
        )
        session.add(message)
        ticket.updated_at = datetime.utcnow()
        if ticket.dialog_open:
            ticket.dialog_last_activity_at = datetime.utcnow()
            ticket.dialog_expires_at = datetime.utcnow() + timedelta(seconds=dialog_timeout_seconds)
        session.commit()
        session.refresh(ticket)
        return ticket


def mark_order_guest_notified(ticket_id: int) -> bool:
    """Пометить заказ как уведомлённый, чтобы bridge не слал дубликат."""
    with SessionLocal() as session:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket or ticket.type != TicketType.MENU_ORDER:
            return False
        payload = dict(ticket.payload or {})
        payload["guest_notified"] = True
        ticket.payload = payload
        ticket.updated_at = datetime.utcnow()
        session.commit()
        return True


def close_dialog_ticket(ticket_id: int) -> bool:
    with SessionLocal() as session:
        ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            return False
        ticket.dialog_open = False
        ticket.dialog_expires_at = None
        ticket.updated_at = datetime.utcnow()
        session.commit()
        return True


def close_expired_open_dialogs() -> int:
    now = datetime.utcnow()
    with SessionLocal() as session:
        expired = (
            session.query(Ticket)
            .filter(
                Ticket.dialog_open == True,
                Ticket.dialog_expires_at.is_not(None),
                Ticket.dialog_expires_at <= now,
            )
            .all()
        )
        if not expired:
            return 0
        for ticket in expired:
            ticket.dialog_open = False
            ticket.dialog_expires_at = None
            ticket.updated_at = now
        session.commit()
        return len(expired)


def list_active_admins(session: Session) -> list[AdminUser]:
    return session.query(AdminUser).filter(AdminUser.is_active == 1).all()


def get_pending_tickets(session: Session) -> list[Ticket]:
    """Get all pending tickets ordered by creation date."""
    return (
        session.query(Ticket)
        .filter(Ticket.status.in_([TicketStatus.PENDING_ADMIN, TicketStatus.NEW]))
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_all_active_tickets(session: Session) -> list[Ticket]:
    """Get all non-completed/non-cancelled tickets."""
    return (
        session.query(Ticket)
        .filter(Ticket.status.in_([TicketStatus.PENDING_ADMIN, TicketStatus.NEW]))
        .order_by(Ticket.created_at.desc())
        .all()
    )


def get_ticket_by_id(session: Session, ticket_id: int) -> Ticket | None:
    """Get ticket by ID with all messages."""
    return session.query(Ticket).filter(Ticket.id == ticket_id).first()


def update_ticket_status(session: Session, ticket_id: int, new_status: TicketStatus) -> bool:
    """Update ticket status."""
    ticket = session.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket:
        ticket.status = new_status
        if new_status in {TicketStatus.COMPLETED, TicketStatus.DECLINED, TicketStatus.CANCELLED}:
            ticket.dialog_open = False
            ticket.dialog_expires_at = None
        ticket.updated_at = datetime.utcnow()
        session.commit()
        return True
    return False


def is_user_admin(session: Session, telegram_id: str) -> bool:
    """Check if user is an active admin."""
    admin = session.query(AdminUser).filter(
        AdminUser.telegram_id == telegram_id,
        AdminUser.is_active == 1
    ).first()
    return admin is not None
