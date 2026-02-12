from __future__ import annotations

from aiogram import Dispatcher

from bot.handlers import (
    admin, in_house, pre_arrival, room_service, start, 
    additional_services, feedback, admin_panel, booking, 
    guide, weather, sos, loyalty, staff, check_in, 
    menu_order, cleaning_schedule, webapp
)


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(admin_panel.router)
    dp.include_router(booking.router)
    dp.include_router(guide.router)
    dp.include_router(weather.router)
    dp.include_router(sos.router)
    dp.include_router(loyalty.router)
    dp.include_router(staff.router)
    dp.include_router(check_in.router)
    dp.include_router(menu_order.router)  # Menu ordering with cart
    dp.include_router(webapp.router) # Web App Data
    dp.include_router(cleaning_schedule.router)  # Cleaning time selection
    dp.include_router(pre_arrival.router)
    dp.include_router(in_house.router)
    dp.include_router(room_service.router)
    dp.include_router(additional_services.router)
    dp.include_router(feedback.router)
