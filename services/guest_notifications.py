from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import GuestBooking
from db.session import SessionLocal
from services.content import content_manager
from services.guest_context import deactivate_expired_guest_bookings, get_local_now, get_local_today


logger = logging.getLogger(__name__)

CHECKOUT_NOTIFICATION_HOUR = 11
CHECKOUT_NOTIFICATION_MINUTE = 30
CHECKIN_NOTIFICATION_HOUR = 10
CHECKIN_NOTIFICATION_MINUTE = 0
FEEDBACK_DELAY_MINUTES = 0
YANDEX_REVIEW_URL = "https://travel.yandex.ru/hotels/republic-of-karelia/baza-otdykha-gora/reviews/"


def build_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оценить проживание", callback_data="start_feedback")]
        ]
    )


def build_checkout_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Помощь / заказать такси", callback_data="checkout_contact_admin")],
        ]
    )


def _detach_all(bookings: list[GuestBooking], db) -> list[GuestBooking]:
    for booking in bookings:
        db.expunge(booking)
    return bookings


def _display_room_number(booking: GuestBooking) -> str:
    room_number = (booking.room_number or "").strip()
    return room_number or "без указанного номера"


def get_checkin_notification_candidates() -> list[GuestBooking]:
    deactivate_expired_guest_bookings()
    today = get_local_today()
    with SessionLocal() as db:
        bookings = db.query(GuestBooking).filter(
            GuestBooking.is_active == True,
            GuestBooking.check_in_date == today,
            GuestBooking.checkin_notified == False,
        ).all()
        return _detach_all(bookings, db)


def get_checkout_notification_candidates() -> list[GuestBooking]:
    deactivate_expired_guest_bookings()
    today = get_local_today()
    with SessionLocal() as db:
        bookings = db.query(GuestBooking).filter(
            GuestBooking.is_active == True,
            GuestBooking.check_out_date == today,
            GuestBooking.checkout_notified == False,
        ).all()
        return _detach_all(bookings, db)


def mark_checkin_notified(booking_id: int) -> None:
    with SessionLocal() as db:
        updated = db.query(GuestBooking).filter(
            GuestBooking.id == booking_id,
            GuestBooking.checkin_notified == False,
        ).update({"checkin_notified": True}, synchronize_session=False)
        if updated:
            db.commit()


def mark_checkout_notified(booking_id: int) -> None:
    with SessionLocal() as db:
        updated = db.query(GuestBooking).filter(
            GuestBooking.id == booking_id,
            GuestBooking.checkout_notified == False,
        ).update({"checkout_notified": True}, synchronize_session=False)
        if updated:
            db.commit()


def get_feedback_candidates() -> list[GuestBooking]:
    today = get_local_today()
    with SessionLocal() as db:
        bookings = db.query(GuestBooking).filter(
            GuestBooking.check_out_date == today,
            GuestBooking.checkout_notified == True,
            GuestBooking.feedback_requested == False,
        ).all()
        return _detach_all(bookings, db)


def mark_feedback_requested(booking_id: int) -> None:
    with SessionLocal() as db:
        updated = db.query(GuestBooking).filter(
            GuestBooking.id == booking_id,
            GuestBooking.feedback_requested == False,
        ).update(
            {
                "feedback_requested": True,
                "feedback_requested_at": get_local_now(),
            },
            synchronize_session=False,
        )
        if updated:
            db.commit()


async def send_checkin_notifications(bot: Bot) -> int:
    bookings = get_checkin_notification_candidates()
    if not bookings:
        return 0

    sent = 0
    for booking in bookings:
        try:
            text = content_manager.get_text("notifications.check_in_welcome").format(
                room_number=_display_room_number(booking)
            )
            await bot.send_message(chat_id=int(booking.telegram_id), text=text)
            mark_checkin_notified(booking.id)
            sent += 1
            logger.info("Sent check-in notification for booking %s", booking.id)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send check-in notification for booking %s: %s", booking.id, exc)
    return sent


async def send_checkout_notifications(bot: Bot) -> int:
    bookings = get_checkout_notification_candidates()
    if not bookings:
        return 0

    sent = 0
    for booking in bookings:
        try:
            reminder = content_manager.get_text("notifications.check_out_reminder").format(
                room_number=_display_room_number(booking)
            )
            await bot.send_message(
                chat_id=int(booking.telegram_id),
                text=reminder,
                reply_markup=build_checkout_keyboard(),
            )
            mark_checkout_notified(booking.id)
            sent += 1
            logger.info("Sent check-out notification for booking %s", booking.id)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send check-out notification for booking %s: %s", booking.id, exc)
    return sent


async def send_feedback_requests(bot: Bot) -> int:
    bookings = get_feedback_candidates()
    if not bookings:
        return 0

    sent = 0
    for booking in bookings:
        try:
            text = content_manager.get_text("notifications.feedback_request")
            await bot.send_message(
                chat_id=int(booking.telegram_id),
                text=text,
                reply_markup=build_feedback_keyboard(),
            )
            mark_feedback_requested(booking.id)
            sent += 1
            logger.info("Sent feedback request for booking %s", booking.id)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send feedback request for booking %s: %s", booking.id, exc)
    return sent


async def guest_notification_loop(bot: Bot) -> None:
    """Poll stay notifications using the hotel's local timezone."""
    logger.info("Guest notification loop started")

    while True:
        try:
            now = get_local_now()
            current_minute = now.hour * 60 + now.minute
            checkout_target_minute = CHECKOUT_NOTIFICATION_HOUR * 60 + CHECKOUT_NOTIFICATION_MINUTE
            checkin_target_minute = CHECKIN_NOTIFICATION_HOUR * 60 + CHECKIN_NOTIFICATION_MINUTE

            # Poll continuously after the target time so reservations synced later in the day
            # still receive their messages without waiting for the next morning.
            if current_minute >= checkout_target_minute:
                sent = await send_checkout_notifications(bot)
                if sent:
                    logger.info("Check-out notification batch sent: %s", sent)

            if current_minute >= checkin_target_minute:
                sent = await send_checkin_notifications(bot)
                if sent:
                    logger.info("Check-in notification batch sent: %s", sent)

            feedback_target_minute = checkout_target_minute + FEEDBACK_DELAY_MINUTES
            if current_minute >= feedback_target_minute:
                sent = await send_feedback_requests(bot)
                if sent:
                    logger.info("Feedback request batch sent: %s", sent)
        except Exception as exc:  # pragma: no cover
            logger.warning("Guest notification loop error: %s", exc)

        await asyncio.sleep(30)
