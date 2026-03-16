from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from services.weather_yandex import fetch_sortavala_weather

router = Router()

@router.callback_query(F.data == "in_weather")
async def show_weather(callback: CallbackQuery):
    await callback.answer()  # Acknowledge immediately to prevent freezing

    weather = await fetch_sortavala_weather()
    if weather:
        details = []
        if weather.wind_speed_ms and weather.wind_direction:
            details.append(f"💨 Ветер: {weather.wind_speed_ms} м/с, {weather.wind_direction}")
        if weather.pressure_mm:
            details.append(f"🧭 Давление: {weather.pressure_mm} мм рт. ст.")
        if weather.humidity_percent:
            details.append(f"💧 Влажность: {weather.humidity_percent}%")

        details_text = "\n".join(details)
        if details_text:
            details_text = f"\n{details_text}\n"

        text = (
            "🌤 <b>Погода в Сортавала (Яндекс):</b>\n"
            f"Сейчас: {weather.temperature_c}°C, {weather.condition}\n"
            f"Ощущается как: {weather.feels_like_c}°C"
            f"{details_text}"
            "\nПодробный прогноз:\n"
            "<a href=\"https://yandex.ru/pogoda/sortavala\">Открыть на Яндекс.Погоде</a>"
        )
    else:
        text = (
            "🌤 Не удалось получить данные Яндекс.Погоды прямо сейчас.\n\n"
            "Подробный прогноз:\n"
            "<a href=\"https://yandex.ru/pogoda/sortavala\">Открыть на Яндекс.Погоде</a>"
        )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_in_house")]
    ])
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
