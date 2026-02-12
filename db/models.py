from __future__ import annotations

from datetime import datetime, date
from enum import Enum

from sqlalchemy import JSON, Column, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class TicketStatus(str, Enum):
    NEW = "NEW"
    PENDING_ADMIN = "PENDING_ADMIN"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"
    CANCELLED = "CANCELLED"


class TicketType(str, Enum):
    ROOM_SERVICE = "ROOM_SERVICE"
    PRE_ARRIVAL = "PRE_ARRIVAL"
    BREAKFAST = "BREAKFAST"
    SOS = "SOS"
    STAFF_TASK = "STAFF_TASK"
    CHECK_IN = "CHECK_IN"
    FEEDBACK = "FEEDBACK"
    MENU_ORDER = "MENU_ORDER"
    CLEANING = "CLEANING"
    OTHER = "OTHER"


class MenuCategory(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


class StaffRole(str, Enum):
    MAID = "maid"
    TECHNICIAN = "technician"
    ADMINISTRATOR = "administrator"


class TicketMessageSender(str, Enum):
    GUEST = "GUEST"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    type: Mapped[TicketType] = mapped_column(SAEnum(TicketType), nullable=False)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.PENDING_ADMIN, nullable=False)

    guest_chat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    guest_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    channel: Mapped[str] = mapped_column(String(32), default="TELEGRAM", nullable=False)

    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    messages: Mapped[list["TicketMessage"]] = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), nullable=False, index=True)
    sender: Mapped[TicketMessageSender] = mapped_column(SAEnum(TicketMessageSender), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Admin information for messages sent by admins
    admin_telegram_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    admin_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="messages")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_visit: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # breakfast, lunch, dinner
    category_type: Mapped[MenuCategory] = mapped_column(SAEnum(MenuCategory), default=MenuCategory.BREAKFAST, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    composition: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{name: "Яйца", quantity: 2, unit: "шт"}, ...]
    price: Mapped[float] = mapped_column(Integer, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_available: Mapped[bool] = mapped_column(default=True, nullable=False)
    admin_comment: Mapped[str | None] = mapped_column(Text, nullable=True)  # Comment for guests


class GuideItem(Base):
    __tablename__ = "guide_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True) # e.g., 'waterfalls', 'cafes'
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    map_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)


class StaffTask(Base):
    __tablename__ = "staff_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_number: Mapped[str] = mapped_column(String(32), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False) # e.g., 'cleaning', 'maintenance'
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # 'PENDING', 'IN_PROGRESS', 'COMPLETED'
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True) # Staff telegram_id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    start_notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class Staff(Base):
    """Staff members with role-based access."""
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)  # Optional, can identify by phone
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)  # Required, unique identifier
    role: Mapped[StaffRole] = mapped_column(SAEnum(StaffRole), nullable=False)
    permissions: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {edit_menu: true, edit_guide: true, ...}
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GuestBooking(Base):
    """Track guest bookings locally for cleaning schedule."""
    __tablename__ = "guest_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    room_number: Mapped[str] = mapped_column(String(32), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_out_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cleaning_requests: Mapped[list["CleaningRequest"]] = relationship("CleaningRequest", back_populates="guest_booking")


class CleaningRequestStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    DECLINED = "DECLINED"


class CleaningRequest(Base):
    """Track daily cleaning schedule choices."""
    __tablename__ = "cleaning_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    guest_booking_id: Mapped[int] = mapped_column(ForeignKey("guest_bookings.id"), nullable=False, index=True)
    requested_date: Mapped[date] = mapped_column(Date, nullable=False)
    requested_time_slot: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g., "12:00-13:00" or None if declined
    status: Mapped[CleaningRequestStatus] = mapped_column(SAEnum(CleaningRequestStatus), default=CleaningRequestStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    guest_booking: Mapped[GuestBooking] = relationship("GuestBooking", back_populates="cleaning_requests")
