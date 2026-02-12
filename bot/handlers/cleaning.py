"""
Cleaning time preference handler
Handles guest responses to daily cleaning time preference requests
"""
from __future__ import annotations

import logging
from datetime import datetime
from aiogram import F, Router
from aiogram.types import CallbackQuery
from db.session import SessionLocal
from db.models import CleaningSchedule, GuestStay, StaffTask

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith("cleaning_time:"))
async def handle_cleaning_time_selection(callback: CallbackQuery) -> None:
    """
    Handle guest's cleaning time preference selection
    Callback data format: cleaning_time:{schedule_id}:{time_slot}
    """
    try:
        # Parse callback data
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("❌ Ошибка обработки запроса")
            return
        
        schedule_id = int(parts[1])
        time_slot = parts[2]
        
        db = SessionLocal()
        
        try:
            # Get cleaning schedule
            schedule = db.query(CleaningSchedule).filter(CleaningSchedule.id == schedule_id).first()
            
            if not schedule:
                await callback.answer("❌ Запрос не найден")
                return
            
            # Check if already responded
            if schedule.response_received:
                await callback.answer("Вы уже выбрали время уборки сегодня")
                return
            
            # Get guest stay info
            stay = db.query(GuestStay).filter(GuestStay.id == schedule.guest_stay_id).first()
            
            if not stay:
                await callback.answer("❌ Информация о проживании не найдена")
                return
            
            # Update schedule with selected time
            schedule.time_slot = time_slot
            schedule.response_received = True
            schedule.response_received_at = datetime.utcnow()
            
            # Create staff task for housekeeping if cleaning is required
            if time_slot != "not_required":
                staff_task = StaffTask(
                    room_number=stay.room_number,
                    task_type="cleaning",
                    description=f"Уборка номера. Желаемое время: {time_slot}",
                    status="PENDING",
                    assigned_to=None  # Will be assigned by admin/housekeeper
                )
                db.add(staff_task)
                
                response_text = (
                    f"✅ Спасибо! Уборка запланирована на {time_slot}\n\n"
                    f"Горничная подойдёт в указанное время."
                )
            else:
                response_text = (
                    "✅ Принято! Уборка номера на сегодня не требуется.\n\n"
                    "Если передумаете, воспользуйтесь кнопкой \"Уборка в номере\" в меню Рум-сервис."
                )
            
            db.commit()
            
            # Update message text to show selection
            try:
                if time_slot != "not_required":
                    confirmation = f"🧹 Выбрано время уборки: {time_slot}"
                else:
                    confirmation = "🧹 Уборка не требуется"
                
                await callback.message.edit_text(
                    f"{callback.message.text}\n\n{confirmation}"
                )
            except Exception as e:
                logger.warning(f"Failed to edit message: {e}")
            
            await callback.answer(response_text, show_alert=True)
            
            logger.info(
                f"Guest {stay.telegram_id} selected cleaning time {time_slot} "
                f"for room {stay.room_number} on {schedule.date}"
            )
        
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Error handling cleaning time selection: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка. Попробуйте позже или свяжитесь с администратором.")
