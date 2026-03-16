from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot

from config import get_settings
from db.models import GuestBooking, ShelterSyncState, User
from db.session import SessionLocal
from services.guest_context import get_local_now, get_local_today
from services.phone_utils import normalize_phone
from services.shelter import PMSGuest, PMSReservation, ShelterAPIError, ShelterPMSClient, get_shelter_pms_client


logger = logging.getLogger(__name__)

SYNC_WINDOW_PAST_DAYS = 1
SYNC_WINDOW_FUTURE_DAYS = 30
STARTUP_DELAY_SECONDS = 30


def _phone_tail(phone: str | None) -> str:
    normalized = normalize_phone(phone)
    if len(normalized) >= 10:
        return normalized[-10:]
    return normalized


def _get_users_with_phones() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with SessionLocal() as db:
        users = db.query(User).filter(User.phone.isnot(None)).all()
        for user in users:
            tail = _phone_tail(user.phone)
            if tail:
                mapping[tail] = user.telegram_id
    return mapping


def _get_or_create_sync_state(db) -> ShelterSyncState:
    state = db.query(ShelterSyncState).filter(ShelterSyncState.id == 1).first()
    if state is None:
        state = ShelterSyncState(id=1)
        db.add(state)
        db.flush()
    return state


def _set_last_sync_at(db) -> None:
    state = _get_or_create_sync_state(db)
    state.last_sync_at = get_local_now()


def _reservation_is_active(reservation: PMSReservation) -> bool:
    today = get_local_today()
    return not reservation.is_annulled and reservation.check_in <= today <= reservation.check_out


def _build_guest_name(reservation: PMSReservation, guest: PMSGuest) -> str | None:
    full_name = " ".join(
        part for part in (guest.first_name, guest.last_name) if part
    ).strip()
    return full_name or reservation.guest_name


def _parse_embedded_guests(client: ShelterPMSClient, reservation: PMSReservation) -> list[PMSGuest]:
    guests: list[PMSGuest] = []
    for item in reservation.guests:
        guest = client._parse_guest(item)  # best-effort reuse of PMS parsing logic
        if guest:
            guests.append(guest)
    return guests


def _deactivate_annulled_booking(db, reservation_id: str) -> int:
    return db.query(GuestBooking).filter(
        GuestBooking.shelter_reservation_id == reservation_id,
        GuestBooking.is_active == True,
    ).update({"is_active": False}, synchronize_session=False)


def _create_or_update_guest_booking(
    db,
    telegram_id: str,
    reservation: PMSReservation,
    guest_name: str | None,
) -> bool:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if user is not None and guest_name and not user.full_name:
        user.full_name = guest_name

    booking = db.query(GuestBooking).filter(
        GuestBooking.telegram_id == telegram_id,
        GuestBooking.shelter_reservation_id == reservation.id,
    ).first()

    if booking is None:
        booking = db.query(GuestBooking).filter(
            GuestBooking.telegram_id == telegram_id,
            GuestBooking.shelter_reservation_id.is_(None),
            GuestBooking.check_in_date == reservation.check_in,
            GuestBooking.check_out_date == reservation.check_out,
        ).first()

    if booking is None:
        booking = GuestBooking(
            telegram_id=telegram_id,
            room_number=reservation.room_number or "",
            check_in_date=reservation.check_in,
            check_out_date=reservation.check_out,
            shelter_reservation_id=reservation.id,
            is_active=_reservation_is_active(reservation),
            checkin_notified=False,
            checkout_notified=False,
            feedback_requested=False,
        )
        db.add(booking)
        return True

    dates_changed = (
        booking.check_in_date != reservation.check_in
        or booking.check_out_date != reservation.check_out
    )
    room_number = reservation.room_number if reservation.room_number is not None else booking.room_number

    booking.room_number = room_number or ""
    booking.check_in_date = reservation.check_in
    booking.check_out_date = reservation.check_out
    booking.shelter_reservation_id = reservation.id
    booking.is_active = _reservation_is_active(reservation)

    if dates_changed:
        booking.checkin_notified = False
        booking.checkout_notified = False
        booking.feedback_requested = False
        booking.feedback_requested_at = None

    return True


async def sync_reservations_once() -> int:
    users_by_phone = _get_users_with_phones()
    with SessionLocal() as db:
        _set_last_sync_at(db)
        db.commit()

    if not users_by_phone:
        logger.info("PMS sync: matched 0 bookings (no users with phones)")
        return 0

    today = get_local_today()
    lived_from = today - timedelta(days=SYNC_WINDOW_PAST_DAYS)
    lived_to = today + timedelta(days=SYNC_WINDOW_FUTURE_DAYS)
    client = get_shelter_pms_client()

    reservations = await client.get_reservations_by_filter(lived_from, lived_to, is_annul=False)
    annulled_reservations = await client.get_reservations_by_filter(lived_from, lived_to, is_annul=True)

    matched = 0
    seen_pairs: set[tuple[str, str]] = set()
    with SessionLocal() as db:
        for reservation in annulled_reservations:
            _deactivate_annulled_booking(db, reservation.id)

        for reservation in [*reservations, *annulled_reservations]:
            guests = _parse_embedded_guests(client, reservation)
            if not guests:
                guests = await client.get_reservation_guests(reservation.id)
            for guest in guests:
                tail = _phone_tail(guest.phone)
                if not tail:
                    continue
                telegram_id = users_by_phone.get(tail)
                if not telegram_id:
                    continue
                pair = (telegram_id, reservation.id)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                if _create_or_update_guest_booking(
                    db=db,
                    telegram_id=telegram_id,
                    reservation=reservation,
                    guest_name=_build_guest_name(reservation, guest),
                ):
                    matched += 1

        _set_last_sync_at(db)
        db.commit()

    logger.info("PMS sync: matched %s bookings", matched)
    return matched


async def shelter_sync_loop(bot: Bot, interval_seconds: int | None = None) -> None:
    """Periodically sync Shelter PMS reservations to local guest bookings."""
    del bot  # reserved for future bot-side sync notifications

    settings = get_settings()
    interval = interval_seconds or settings.shelter_sync_interval
    if not settings.shelter_pms_token:
        logger.warning("Shelter PMS sync disabled: SHELTER_PMS_TOKEN is not configured")
        return

    logger.info("Shelter PMS sync loop started")
    await asyncio.sleep(STARTUP_DELAY_SECONDS)

    while True:
        try:
            await sync_reservations_once()
        except ShelterAPIError as exc:  # pragma: no cover
            logger.warning("Shelter PMS sync failed: %s", exc.message or exc)
        except Exception as exc:  # pragma: no cover
            logger.warning("Unexpected Shelter PMS sync error: %s", exc)

        await asyncio.sleep(max(int(interval), 30))
