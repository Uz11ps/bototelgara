from __future__ import annotations

from aiogram.types import ReplyKeyboardMarkup

from bot.keyboards.main_menu import build_main_reply_keyboard, build_staff_reply_keyboard
from db.models import Staff, StaffRole
from db.session import SessionLocal


def build_role_reply_keyboard(user_id: str) -> ReplyKeyboardMarkup:
    """Return staff keyboard for workers, otherwise default user keyboard."""
    with SessionLocal() as session:
        staff = (
            session.query(Staff)
            .filter(Staff.telegram_id == user_id, Staff.is_active == True)
            .first()
        )
        if staff and staff.role in {StaffRole.MAID, StaffRole.TECHNICIAN}:
            return build_staff_reply_keyboard()
    return build_main_reply_keyboard()
