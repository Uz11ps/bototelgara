from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from sqlalchemy.orm import Session

from db.models import AdminUser, Ticket, TicketMessage, TicketMessageSender, TicketStatus, TicketType
from db.session import SessionLocal


logger = logging.getLogger(__name__)

RATE_LIMIT_MAX_TICKETS = 3
RATE_LIMIT_WINDOW_SECONDS = 60


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
