"""
Daily cleaning schedule notification service
Sends automatic cleaning time preference requests to guests
"""
import logging
import asyncio
from datetime import date, datetime
from typing import Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from db.session import SessionLocal
from db.models import GuestStay, CleaningSchedule

logger = logging.getLogger(__name__)


class CleaningScheduler:
    """Manages daily cleaning time preference notifications"""
    
    def __init__(self, bot: Bot, notification_time: str = "11:00"):
        """
        Initialize the cleaning scheduler
        
        Args:
            bot: Telegram Bot instance
            notification_time: Time to send daily notifications (HH:MM format, default: 11:00)
        """
        self.bot = bot
        self.scheduler = AsyncIOScheduler()
        self.notification_time = notification_time
        self._parse_notification_time()
    
    def _parse_notification_time(self):
        """Parse notification time string into hour and minute"""
        try:
            hour, minute = map(int, self.notification_time.split(":"))
            self.notification_hour = hour
            self.notification_minute = minute
        except Exception as e:
            logger.error(f"Invalid notification time format: {self.notification_time}. Using default 11:00")
            self.notification_hour = 11
            self.notification_minute = 0
    
    def start(self):
        """Start the scheduler"""
        # Schedule daily cleaning notifications
        self.scheduler.add_job(
            self.send_daily_cleaning_requests,
            trigger=CronTrigger(
                hour=self.notification_hour,
                minute=self.notification_minute,
                timezone="Europe/Moscow"
            ),
            id="daily_cleaning_notifications",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"✅ Cleaning scheduler started - daily notifications at {self.notification_time} Moscow time")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Cleaning scheduler stopped")
    
    async def send_daily_cleaning_requests(self):
        """Send cleaning time preference requests to all active guests"""
        logger.info("Starting daily cleaning notification job...")
        
        today = date.today()
        db = SessionLocal()
        
        try:
            # Get all active stays
            active_stays = (
                db.query(GuestStay)
                .filter(
                    GuestStay.is_active == True,
                    GuestStay.auto_cleaning_enabled == True,
                    GuestStay.check_in_date < today,  # Not check-in day
                    GuestStay.check_out_date > today   # Not check-out day
                )
                .all()
            )
            
            logger.info(f"Found {len(active_stays)} active stays for cleaning notifications")
            
            for stay in active_stays:
                # Check if notification already sent today
                existing_schedule = (
                    db.query(CleaningSchedule)
                    .filter(
                        CleaningSchedule.guest_stay_id == stay.id,
                        CleaningSchedule.date == today,
                        CleaningSchedule.notification_sent == True
                    )
                    .first()
                )
                
                if existing_schedule:
                    logger.debug(f"Notification already sent to guest {stay.telegram_id} for room {stay.room_number}")
                    continue
                
                # Send notification to guest
                try:
                    await self.send_cleaning_request(stay, today, db)
                    logger.info(f"✅ Sent cleaning request to guest {stay.telegram_id} in room {stay.room_number}")
                except Exception as e:
                    logger.error(f"Failed to send cleaning request to {stay.telegram_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error in daily cleaning notification job: {e}", exc_info=True)
        finally:
            db.close()
    
    async def send_cleaning_request(self, stay: GuestStay, today: date, db):
        """Send cleaning time preference request to a specific guest"""
        # Create or update cleaning schedule record
        schedule = (
            db.query(CleaningSchedule)
            .filter(
                CleaningSchedule.guest_stay_id == stay.id,
                CleaningSchedule.date == today
            )
            .first()
        )
        
        if not schedule:
            schedule = CleaningSchedule(
                guest_stay_id=stay.id,
                date=today,
                notification_sent=False,
                response_received=False
            )
            db.add(schedule)
            db.flush()
        
        # Create inline keyboard with time slot options
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="12:00-13:00", callback_data=f"cleaning_time:{schedule.id}:12:00-13:00")],
            [InlineKeyboardButton(text="13:00-14:00", callback_data=f"cleaning_time:{schedule.id}:13:00-14:00")],
            [InlineKeyboardButton(text="14:00-15:00", callback_data=f"cleaning_time:{schedule.id}:14:00-15:00")],
            [InlineKeyboardButton(text="15:00-16:00", callback_data=f"cleaning_time:{schedule.id}:15:00-16:00")],
            [InlineKeyboardButton(text="16:00-17:00", callback_data=f"cleaning_time:{schedule.id}:16:00-17:00")],
            [InlineKeyboardButton(text="Уборка не требуется", callback_data=f"cleaning_time:{schedule.id}:not_required")]
        ])
        
        message_text = (
            f"🧹 Добрый день!\n\n"
            f"Во сколько сегодня для Вас будет удобно провести уборку номера {stay.room_number}?"
        )
        
        # Send message to guest
        await self.bot.send_message(
            chat_id=int(stay.telegram_id),
            text=message_text,
            reply_markup=keyboard
        )
        
        # Update schedule record
        schedule.notification_sent = True
        schedule.notification_sent_at = datetime.utcnow()
        db.commit()
    
    async def manual_cleaning_request(self, telegram_id: str, room_number: str):
        """
        Handle manual cleaning request from guest (via room service button)
        This is separate from the automated daily request
        """
        # This will be handled in the existing room_service.py handler
        # We just need to differentiate it from the automated request
        pass


# Singleton instance
_scheduler: Optional[CleaningScheduler] = None


def get_cleaning_scheduler(bot: Bot, notification_time: str = "11:00") -> CleaningScheduler:
    """Get or create the cleaning scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = CleaningScheduler(bot, notification_time)
    return _scheduler
