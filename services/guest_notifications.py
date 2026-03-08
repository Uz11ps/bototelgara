from __future__ import annotations

import asyncio
import logging
from datetime import date

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from db.models import GuestBooking
from db.session import SessionLocal
from services.content import content_manager
from services.guest_context import deactivate_expired_guest_bookings, get_local_now, get_local_today


logger = logging.getLogger(__name__)

CHECKOUT_NOTIFICATION_HOUR = 9
CHECKIN_NOTIFICATION_HOUR = 10


def build_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Оставить отзыв", callback_data="start_feedback")]
        ]
    )


def _detach_all(bookings: list[GuestBooking], db) -> list[GuestBooking]:
    for booking in bookings:
        db.expunge(booking)
    return bookings


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


async def send_checkin_notifications(bot: Bot) -> int:
    bookings = get_checkin_notification_candidates()
    if not bookings:
        return 0

    sent = 0
    for booking in bookings:
        try:
            text = content_manager.get_text("notifications.check_in_welcome").format(
                room_number=booking.room_number
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
                room_number=booking.room_number
            )
            feedback_invite = content_manager.get_text("notifications.check_out_feedback")
            await bot.send_message(chat_id=int(booking.telegram_id), text=reminder)
            await bot.send_message(
                chat_id=int(booking.telegram_id),
                text=feedback_invite,
                reply_markup=build_feedback_keyboard(),
            )
            mark_checkout_notified(booking.id)
            sent += 1
            logger.info("Sent check-out notification for booking %s", booking.id)
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to send check-out notification for booking %s: %s", booking.id, exc)
    return sent


async def guest_notification_loop(bot: Bot) -> None:
    """Send one-time daily stay notifications using the hotel's local timezone."""
    logger.info("Guest notification loop started")
    last_checkin_run: date | None = None
    last_checkout_run: date | None = None

    while True:
        try:
            now = get_local_now()
            today = now.date()

            if now.hour >= CHECKOUT_NOTIFICATION_HOUR and last_checkout_run != today:
                sent = await send_checkout_notifications(bot)
                last_checkout_run = today
                if sent:
                    logger.info("Check-out notification batch sent: %s", sent)

            if now.hour >= CHECKIN_NOTIFICATION_HOUR and last_checkin_run != today:
                sent = await send_checkin_notifications(bot)
                last_checkin_run = today
                if sent:
                    logger.info("Check-in notification batch sent: %s", sent)
        except Exception as exc:  # pragma: no cover
            logger.warning("Guest notification loop error: %s", exc)

        await asyncio.sleep(30)
