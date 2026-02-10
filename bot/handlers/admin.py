"""
Admin commands handler
Provides administrative functions like hotel status check
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from services.shelter import get_shelter_client, ShelterAPIError
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("hotelstatus", "status"))
async def cmd_hotel_status(message: Message) -> None:
    """
    Check current hotel occupancy status
    Command: /hotelstatus or /status
    """
    try:
        await message.answer("🔍 Получаю данные из Shelter Cloud PMS...")
        
        shelter = get_shelter_client()
        
        # Test API connectivity first
        try:
            ping_result = await shelter.ping()
            logger.info(f"Shelter API ping successful: {ping_result}")
        except Exception as e:
            logger.warning(f"Shelter API ping failed: {e}")
        
        # Get hotel statistics
        stats = await shelter.get_hotel_stats()
        
        # Format response
        status_text = (
            f"🏨 <b>Статус отеля GORA</b>\n\n"
            f"📊 <b>Номерной фонд:</b>\n"
            f"• Всего номеров: {stats.total_rooms}\n"
            f"• Занято: {stats.occupied_rooms}\n"
            f"• Свободно: {stats.available_rooms}\n\n"
            f"📈 <b>Загруженность:</b> {stats.occupancy_rate:.1%}\n\n"
            f"🕐 Обновлено: {stats.last_updated.strftime('%d.%m.%Y %H:%M')}\n\n"
        )
        
        # Add status bar
        occupied_bars = int(stats.occupancy_rate * 10)
        status_bar = "🟩" * occupied_bars + "⬜" * (10 - occupied_bars)
        status_text += f"{status_bar}\n\n"
        
        # Add note about API status
        if stats.total_rooms == 50 and stats.occupied_rooms == 32:
            status_text += (
                "⚠️ <i>Примечание: отображаются тестовые данные. "
                "Для получения реальных данных из Shelter Cloud необходимо "
                "настроить правильные API endpoints в техподдержке Shelter.</i>"
            )
        
        await message.answer(status_text, parse_mode="HTML")
    
    except ShelterAPIError as e:
        logger.error(f"Shelter API error: {e}")
        await message.answer(
            f"❌ Ошибка при получении данных из Shelter API:\n{str(e)}\n\n"
            f"Проверьте настройки API токенов."
        )
    
    except Exception as e:
        logger.error(f"Error getting hotel status: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении статуса отеля. "
            "Пожалуйста, попробуйте позже."
        )


@router.message(Command("rooms", "availability"))
async def cmd_room_availability(message: Message) -> None:
    """
    Check room availability
    Command: /rooms or /availability
    """
    try:
        await message.answer("🔍 Проверяю доступность номеров...")
        
        shelter = get_shelter_client()
        rooms = await shelter.get_room_availability()
        
        if not rooms:
            await message.answer("ℹ️ Нет данных о доступности номеров.")
            return
        
        # Group by availability
        available = [r for r in rooms if r.is_available]
        occupied = [r for r in rooms if not r.is_available]
        
        response_text = "🏨 <b>Доступность номеров</b>\n\n"
        
        if available:
            response_text += "✅ <b>Свободные номера:</b>\n"
            for room in available:
                price_str = f"{room.price:,.0f} ₽" if room.price else "—"
                capacity_str = f"({room.capacity} чел.)" if room.capacity else ""
                response_text += f"• {room.room_name} {capacity_str} — {price_str}\n"
            response_text += "\n"
        
        if occupied:
            response_text += f"🔒 <b>Занято:</b> {len(occupied)} номеров\n\n"
        
        # Add note for mock data
        if len(rooms) == 2 and rooms[0].room_name == "Стандарт":
            response_text += (
                "\n⚠️ <i>Примечание: отображаются тестовые данные. "
                "Для получения реальных данных необходима настройка Shelter API.</i>"
            )
        
        await message.answer(response_text, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Error getting room availability: {e}", exc_info=True)
        await message.answer(
            "❌ Ошибка при получении данных о номерах. "
            "Попробуйте позже."
        )


@router.message(Command("sheltertest"))
async def cmd_shelter_test(message: Message) -> None:
    """
    Test Shelter API connection
    Admin command for debugging
    """
    try:
        await message.answer("🔧 Тестирую подключение к Shelter API...")
        
        shelter = get_shelter_client()
        
        # Test ping
        try:
            ping_result = await shelter.ping()
            ping_status = f"✅ Ping: OK ({ping_result})"
        except Exception as e:
            ping_status = f"❌ Ping: Failed ({str(e)[:100]})"
        
        # Test hotel info
        try:
            hotel_info = await shelter.get_hotel_info()
            hotel_status = f"✅ Hotel Info: OK"
        except Exception as e:
            hotel_status = f"❌ Hotel Info: Failed ({str(e)[:100]})"
        
        # Test availability
        try:
            rooms = await shelter.get_room_availability()
            avail_status = f"✅ Availability: OK ({len(rooms)} rooms)"
        except Exception as e:
            avail_status = f"❌ Availability: Failed ({str(e)[:100]})"
        
        response = (
            f"<b>Shelter API Test Results:</b>\n\n"
            f"{ping_status}\n"
            f"{hotel_status}\n"
            f"{avail_status}\n\n"
            f"<i>Base URL: https://cloud.shelter.ru</i>"
        )
        
        await message.answer(response, parse_mode="HTML")
    
    except Exception as e:
        logger.error(f"Shelter test failed: {e}", exc_info=True)
        await message.answer(f"❌ Test failed: {str(e)}")
