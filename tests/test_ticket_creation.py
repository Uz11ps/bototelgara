import os

import pytest

from db.models import Ticket, TicketMessage, TicketMessageSender, TicketStatus, TicketType
from db.session import SessionLocal, engine
from db.base import Base
from services.tickets import create_ticket


@pytest.fixture(scope="module", autouse=True)
def setup_database() -> None:
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)


def test_create_ticket_persists_ticket_and_message() -> None:
    ticket = create_ticket(
        type_=TicketType.ROOM_SERVICE,
        guest_chat_id="12345",
        guest_name="Test User",
        room_number="101",
        payload={"branch": "technical_problem", "category": "Wi‑Fi"},
        initial_message="Тестовая заявка",
    )

    with SessionLocal() as session:
        db_ticket = session.get(Ticket, ticket.id)
        assert db_ticket is not None
        assert db_ticket.status == TicketStatus.PENDING_ADMIN
        assert db_ticket.type == TicketType.ROOM_SERVICE

        messages = session.query(TicketMessage).filter(TicketMessage.ticket_id == ticket.id).all()
        assert len(messages) == 1
        assert messages[0].sender == TicketMessageSender.GUEST
        assert messages[0].content == "Тестовая заявка"
