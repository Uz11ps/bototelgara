"""
Scheduler for checking staff tasks and sending notifications.
"""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from db.session import SessionLocal
from db.models import StaffTask, Staff
from services.bot_api_bridge import get_bot_bridge
from config import get_settings

logger = logging.getLogger(__name__)


def to_local_naive(dt: datetime) -> datetime:
    """Normalize datetime to local naive for consistent comparisons."""
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt

async def task_scheduler_loop(bot):
    """Loop to check for scheduled tasks."""
    logger.info("Task Scheduler started")
    while True:
        try:
            await check_scheduled_tasks(bot)
        except Exception as e:
            logger.error(f"Error in task scheduler: {e}")
        
        # Check every minute
        await asyncio.sleep(60)

async def check_scheduled_tasks(bot):
    """Check database for tasks that need notifications."""
    db = SessionLocal()
    try:
        now = datetime.now()
        # Find tasks scheduled within next 15 minutes that haven't been notified
        # OR tasks that are due now
        
        # Look ahead 16 minutes to catch the 15-minute window
        window_end = now + timedelta(minutes=16)
        
        tasks = db.query(StaffTask).filter(
            StaffTask.status == "PENDING",
            StaffTask.scheduled_at != None,
            StaffTask.scheduled_at <= window_end
        ).all()
        
        for task in tasks:
            task_time = to_local_naive(task.scheduled_at)
            # Calculate time difference in minutes
            # positive = future, negative = past
            time_diff = (task_time - now).total_seconds() / 60
            
            # 1. Reminder (15 mins before)
            # If between 0 and 15 mins (inclusive), and not sent
            if 0 < time_diff <= 15 and not task.reminder_sent:
                 await send_task_notification(bot, task, db, is_start=False)

            # 2. Start Notification (At time or slightly late)
            # If time_diff <= 0 (it's time!), and not sent
            if time_diff <= 0 and not task.start_notification_sent:
                 await send_task_notification(bot, task, db, is_start=True)
                
    finally:
        db.close()

async def send_task_notification(bot, task: StaffTask, db: Session, is_start: bool = False):
    """Send notification to assigned staff."""
    if not task.assigned_to:
        return

    # Try by telegram_id first
    staff = db.query(Staff).filter(Staff.telegram_id == task.assigned_to).first()
    # Backward compatibility: some old tasks might store staff.id in assigned_to
    if not staff and str(task.assigned_to).isdigit():
        staff = db.query(Staff).filter(Staff.id == int(task.assigned_to)).first()
        if staff and staff.telegram_id:
            task.assigned_to = str(staff.telegram_id)
            db.commit()

    if not staff or not staff.telegram_id:
        logger.warning(f"Cannot notify staff with telegram_id {task.assigned_to} for task {task.id}: Staff not found or no Telegram ID")
        return

    try:
        title = "🚀 <b>ЗАДАЧА НАЧАЛАСЬ!</b>" if is_start else "⏰ <b>Напоминание о задаче</b>"
        
        msg = f"{title}\n\n"
        msg += f"🏨 <b>Комната:</b> {task.room_number}\n"
        msg += f"📌 <b>Тип:</b> {task.desc_type if hasattr(task, 'desc_type') else task.task_type}\n"
        msg += f"🕒 <b>Время:</b> {task.scheduled_at.strftime('%H:%M')}\n"
        if task.description:
            msg += f"\n📝 {task.description}"
        
        await bot.send_message(
            chat_id=staff.telegram_id,
            text=msg,
            parse_mode="HTML"
        )
        logger.info(f"Sent {'start' if is_start else 'reminder'} notification for task {task.id} to {staff.full_name}")
        
        # Mark as notified
        if is_start:
            task.start_notification_sent = True
        else:
            task.reminder_sent = True
            
        db.commit()
        
    except Exception as e:
        logger.error(f"Failed to send notification for task {task.id}: {e}")
