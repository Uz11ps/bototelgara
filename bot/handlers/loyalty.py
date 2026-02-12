from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from db.session import SessionLocal
from db.models import User
from bot.utils.reply_texts import button_text

router = Router()

@router.callback_query(F.data == "in_loyalty")
async def show_loyalty(callback: CallbackQuery):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    
    with SessionLocal() as db:
        user = db.query(User).filter(User.telegram_id == str(callback.from_user.id)).first()
        
        if not user:
            # Создаем пользователя если нет
            user = User(telegram_id=str(callback.from_user.id), full_name=callback.from_user.full_name, loyalty_points=100)
            db.add(user)
            db.commit()
            db.refresh(user)
        
        text = (
            f"👤 <b>Личный кабинет гостя</b>\n\n"
            f"Имя: {user.full_name}\n"
            f"Статус: <b>Постоянный гость</b>\n"
            f"Баллы лояльности: <b>{user.loyalty_points}</b>\n\n"
            f"🎁 <i>Ваши баллы можно использовать для оплаты завтраков или рум-сервиса (1 балл = 1 рубль).</i>"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text("loyalty_history"), callback_data="loyalty_history")],
        [InlineKeyboardButton(text=button_text("loyalty_info"), callback_data="loyalty_info")],
        [InlineKeyboardButton(text=button_text("guide_back"), callback_data="back_to_in_house")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass  # Ignore if message unchanged
