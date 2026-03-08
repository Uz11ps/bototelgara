from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from db.models import GuestBooking
from db.session import SessionLocal

try:
    HOTEL_TIMEZONE = ZoneInfo("Europe/Moscow")
except ZoneInfoNotFoundError:
    HOTEL_TIMEZONE = timezone(timedelta(hours=3), name="Europe/Moscow")


def get_local_now() -> datetime:
    """Return the current hotel-local datetime."""
    return datetime.now(HOTEL_TIMEZONE)


def get_local_today() -> date:
    """Return the current hotel-local date."""
    return get_local_now().date()


def deactivate_expired_guest_bookings() -> int:
    """Deactivate stays where checkout date has already passed."""
    today = get_local_today()
    with SessionLocal() as db:
        updated = db.query(GuestBooking).filter(
            GuestBooking.is_active == True,
            GuestBooking.check_out_date < today,
        ).update({"is_active": False}, synchronize_session=False)
        if updated:
            db.commit()
        return int(updated or 0)


def get_active_guest_booking(telegram_id: str) -> GuestBooking | None:
    """Return active booking for a guest, detached from session."""
    deactivate_expired_guest_bookings()
    with SessionLocal() as db:
        booking = db.query(GuestBooking).filter(
            GuestBooking.telegram_id == telegram_id,
            GuestBooking.is_active == True,
        ).first()
        if booking:
            db.expunge(booking)
        return booking


def get_active_room_number(telegram_id: str) -> str | None:
    booking = get_active_guest_booking(telegram_id)
    if not booking:
        return None
    room_number = (booking.room_number or "").strip()
    return room_number or None
