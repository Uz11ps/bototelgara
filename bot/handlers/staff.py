from aiogram import Router, F
from aiogram.types import Message
from db.session import SessionLocal
from db.models import StaffTask

router = Router()

@router.message(F.text.startswith("/staff"))
async def staff_login(message: Message):
    # Упрощенная проверка для персонала
    if "gora_staff" not in message.text:
        return
    
    db = SessionLocal()
    tasks = db.query(StaffTask).filter(StaffTask.status == "PENDING").all()
    db.close()
    
    if not tasks:
        await message.answer("🛠 <b>Панель персонала</b>\n\nАктивных задач пока нет. Отдыхайте!")
        return
    
    text = "🛠 <b>Активные задачи:</b>\n\n"
    for task in tasks:
        text += f"📍 Номер {task.room_number}: {task.task_type}\n{task.description}\n\n"
    
    await message.answer(text, parse_mode="HTML")
