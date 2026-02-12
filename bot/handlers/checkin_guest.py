"""
Guest self check-in handler
Allows guests to register their stay using a check-in code
"""
from __future__ import annotations

import logging
from datetime import datetime
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot.states import FlowState
from db.session import SessionLocal
from db.models import GuestStay

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, state: FSMContext) -> None:
    """
    Start check-in process
    Usage: /checkin
    """
    await state.set_state(FlowState.guest_checkin_code)
    await message.answer(
        "🏨 <b>Добро пожаловать в отель GORA!</b>\n\n"
        "Для регистрации заезда введите код, который вы получили при бронировании.\n\n"
        "Формат кода: например, <code>ROOM101</code>",
        parse_mode="HTML"
    )


@router.message(FlowState.guest_checkin_code)
async def process_checkin_code(message: Message, state: FSMContext) -> None:
    """
    Process check-in code and link guest to stay
    """
    code = (message.text or "").strip().upper()
    
    if not code:
        await message.answer("❌ Пожалуйста, введите код регистрации")
        return
    
    db = SessionLocal()
    
    try:
        # Find guest stay by check-in code
        stay = (
            db.query(GuestStay)
            .filter(
                GuestStay.checkin_code == code,
                GuestStay.is_active == True
            )
            .first()
        )
        
        if not stay:
            await message.answer(
                "❌ Код регистрации не найден или не активен.\n\n"
                "Пожалуйста, проверьте код или свяжитесь с администратором."
            )
            await state.clear()
            return
        
        # Check if stay is already linked to another user
        if stay.telegram_id and stay.telegram_id != str(message.from_user.id):
            await message.answer(
                "⚠️ Этот код уже используется другим гостем.\n\n"
                "Если это ошибка, пожалуйста, свяжитесь с администратором."
            )
            await state.clear()
            return
        
        # Link telegram ID and username to the stay
        stay.telegram_id = str(message.from_user.id)
        stay.telegram_username = message.from_user.username
        if not stay.guest_name and message.from_user.full_name:
            stay.guest_name = message.from_user.full_name
        stay.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Success message
        check_in_str = stay.check_in_date.strftime("%d.%m.%Y")
        check_out_str = stay.check_out_date.strftime("%d.%m.%Y")
        
        await message.answer(
            f"✅ <b>Регистрация успешно завершена!</b>\n\n"
            f"🏨 Номер: <b>{stay.room_number}</b>\n"
            f"📅 Заезд: {check_in_str}\n"
            f"📅 Выезд: {check_out_str}\n\n"
            f"{'🧹 Вы будете получать ежедневные запросы на удобное время уборки номера.' if stay.auto_cleaning_enabled else ''}\n\n"
            f"Приятного отдыха! 🎉",
            parse_mode="HTML"
        )
        
        logger.info(
            f"Guest checked in: telegram_id={stay.telegram_id}, "
            f"username={stay.telegram_username}, room={stay.room_number}"
        )
        
    except Exception as e:
        logger.error(f"Error during check-in: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже или свяжитесь с администратором."
        )
    finally:
        db.close()
        await state.clear()
