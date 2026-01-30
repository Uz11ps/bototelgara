from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp

router = Router()

@router.callback_query(F.data == "in_weather")
async def show_weather(callback: CallbackQuery):
    # В реальном проекте здесь был бы запрос к API погоды
    # Для скорости выводим текущую ситуацию и ссылки на камеры
    text = (
        "🌤 <b>Погода в Сортавала:</b> -3°C, Облачно\n"
        "🌲 <b>Парк Рускеала:</b> -5°C, Снег\n\n"
        "🎥 <b>Онлайн-камеры:</b>\n"
        "В Карелии временно ограничены публичные трансляции Ситилинк, но мы работаем над подключением внутренних камер базы."
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_in_house")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
