from __future__ import annotations

from aiogram import Dispatcher

from bot.handlers import admin, in_house, pre_arrival, room_service, start, additional_services, feedback, admin_panel


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(admin_panel.router)
    dp.include_router(pre_arrival.router)
    dp.include_router(in_house.router)
    dp.include_router(room_service.router)
    dp.include_router(additional_services.router)
    dp.include_router(feedback.router)
