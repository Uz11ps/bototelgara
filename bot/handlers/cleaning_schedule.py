"""
Automatic cleaning schedule handler.
Sends daily cleaning time prompts at 11:00 to guests who are staying (not check-in/check-out day).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, date, time, timedelta

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.main_menu import build_cleaning_time_keyboard, build_in_house_menu
from bot.states import FlowState
from db.models import GuestBooking, CleaningRequest, CleaningRequestStatus, TicketType
from db.session import SessionLocal
from services.content import content_manager
from services.tickets import create_ticket
from services.admins import notify_admins_about_ticket


router = Router()
logger = logging.getLogger(__name__)

# Global reference to bot for scheduler
_bot_instance: Bot | None = None


def set_bot_instance(bot: Bot) -> None:
    """Set bot instance for scheduler to use."""
    global _bot_instance
    _bot_instance = bot


def get_eligible_guests_for_cleaning() -> list[GuestBooking]:
    """
    Get guests who should receive cleaning prompts today.
    Criteria: today is NOT check-in date AND NOT check-out date.
    """
    today = date.today()
    
    with SessionLocal() as db:
        bookings = db.query(GuestBooking).filter(
            GuestBooking.is_active == True,
            GuestBooking.check_in_date < today,  # Already checked in
            GuestBooking.check_out_date > today,  # Not checking out today
        ).all()
        
        # Detach from session
        for booking in bookings:
            db.expunge(booking)
        
        return bookings


def has_cleaning_request_today(guest_booking_id: int) -> bool:
    """Check if guest already has a cleaning request for today."""
    today = date.today()
    
    with SessionLocal() as db:
        request = db.query(CleaningRequest).filter(
            CleaningRequest.guest_booking_id == guest_booking_id,
            CleaningRequest.requested_date == today,
        ).first()
        
        return request is not None


def create_cleaning_request(guest_booking_id: int, time_slot: str | None, status: CleaningRequestStatus) -> CleaningRequest:
    """Create a cleaning request record."""
    today = date.today()
    
    with SessionLocal() as db:
        request = CleaningRequest(
            guest_booking_id=guest_booking_id,
            requested_date=today,
            requested_time_slot=time_slot,
            status=status,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        db.expunge(request)
        return request


async def send_cleaning_prompts() -> None:
    """Send cleaning time prompts to all eligible guests."""
    global _bot_instance
    
    if not _bot_instance:
        logger.warning("Bot instance not set, cannot send cleaning prompts")
        return
    
    guests = get_eligible_guests_for_cleaning()
    logger.info(f"Found {len(guests)} guests eligible for cleaning prompts")
    
    for guest in guests:
        # Skip if already has request today
        if has_cleaning_request_today(guest.id):
            logger.debug(f"Guest {guest.telegram_id} already has cleaning request today, skipping")
            continue
        
        try:
            text = content_manager.get_text("cleaning.schedule_prompt")
            await _bot_instance.send_message(
                chat_id=int(guest.telegram_id),
                text=text,
                reply_markup=build_cleaning_time_keyboard(),
            )
            logger.info(f"Sent cleaning prompt to guest {guest.telegram_id}")
        except Exception as e:
            logger.error(f"Failed to send cleaning prompt to {guest.telegram_id}: {e}")


async def cleaning_scheduler_loop() -> None:
    """Background loop that checks time and sends cleaning prompts at 11:00."""
    logger.info("Cleaning scheduler started")
    
    while True:
        now = datetime.now()
        target_time = time(11, 0)  # 11:00 AM
        
        # Check if it's 11:00
        if now.hour == 11 and now.minute == 0:
            logger.info("It's 11:00, sending cleaning prompts")
            await send_cleaning_prompts()
            # Wait 60 seconds to avoid sending again in the same minute
            await asyncio.sleep(60)
        else:
            # Sleep for 30 seconds and check again
            await asyncio.sleep(30)


# --- Callback Handlers ---

@router.callback_query(F.data.startswith("cleaning_"))
async def handle_cleaning_selection(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle cleaning time selection from daily prompt."""
    await callback.answer()
    
    action = callback.data.replace("cleaning_", "")
    
    # Find guest booking for this user
    telegram_id = str(callback.from_user.id)
    
    with SessionLocal() as db:
        booking = db.query(GuestBooking).filter(
            GuestBooking.telegram_id == telegram_id,
            GuestBooking.is_active == True,
        ).first()
        
        if not booking:
            await callback.message.answer("Не найдена информация о вашем проживании.")
            return
        
        booking_id = booking.id
        room_number = booking.room_number
    
    if action == "not_needed":
        # Guest doesn't need cleaning today
        create_cleaning_request(booking_id, None, CleaningRequestStatus.DECLINED)
        
        text = content_manager.get_text("cleaning.not_needed_confirmed")
        await callback.message.answer(text)
    else:
        # Parse time slot from action (e.g., "12_13" -> "12:00-13:00")
        parts = action.split("_")
        if len(parts) == 2:
            time_slot = f"{parts[0]}:00-{parts[1]}:00"
        else:
            time_slot = action
        
        # Create cleaning request
        request = create_cleaning_request(booking_id, time_slot, CleaningRequestStatus.CONFIRMED)
        
        # Send confirmation to guest
        text = content_manager.get_text("cleaning.time_confirmed").format(time_slot=time_slot)
        await callback.message.answer(text)
        
        # Create ticket for staff
        summary = f"Уборка номера {room_number} запланирована на {time_slot}"
        
        try:
            ticket = create_ticket(
                type_=TicketType.CLEANING,
                guest_chat_id=telegram_id,
                guest_name=callback.from_user.full_name,
                room_number=room_number,
                payload={
                    "branch": "cleaning_schedule",
                    "time_slot": time_slot,
                    "cleaning_request_id": request.id,
                },
                initial_message=summary,
            )
            
            # Notify admins
            bot: Bot = callback.bot  # type: ignore
            await notify_admins_about_ticket(bot, ticket, summary)
            
        except Exception as e:
            logger.error(f"Failed to create cleaning ticket: {e}")
