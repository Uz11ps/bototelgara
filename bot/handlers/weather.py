from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
from bot.utils.reply_texts import button_text

router = Router()

@router.callback_query(F.data == "in_weather")
async def show_weather(callback: CallbackQuery):
    await callback.answer()  # Acknowledge immediately to prevent freezing
    
    # В реальном проекте здесь был бы запрос к API погоды
    # Для скорости выводим текущую ситуацию и ссылки на камеры
    text = (
        "🌤 <b>Погода в Сортавала:</b> -3°C, Облачно\n"
        "🌲 <b>Парк Рускеала:</b> -5°C, Снег\n\n"
        "🎥 <b>Онлайн-камеры:</b>\n"
        "В данный момент онлайн-трансляции с камер недоступны. Пожалуйста, уточните у администратора актуальные виды и погоду на базе."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=button_text("weather_back"), callback_data="back_to_in_house")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        pass  # Ignore if message unchanged
