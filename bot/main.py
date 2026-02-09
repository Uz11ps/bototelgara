from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_settings
from db.session import init_db
from bot.handlers import register_handlers
from bot.middleware import ThrottlingMiddleware, CallbackAnswerMiddleware
from bot.handlers.cleaning_schedule import set_bot_instance, cleaning_scheduler_loop
from services.bot_api_bridge import get_bot_bridge


logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Register middleware for performance optimization
    # ThrottlingMiddleware: prevents duplicate rapid clicks (0.5s between clicks)
    # CallbackAnswerMiddleware: ensures all callbacks are answered to prevent "loading" spinner
    dp.callback_query.middleware(ThrottlingMiddleware(throttle_time=0.25))
    dp.callback_query.middleware(CallbackAnswerMiddleware())

    register_handlers(dp)
    
    # Start bot API bridge for delivering admin messages
    bridge = get_bot_bridge(bot)
    await bridge.start()
    
    # Set bot instance for cleaning scheduler
    set_bot_instance(bot)
    
    # Start cleaning scheduler in background
    asyncio.create_task(cleaning_scheduler_loop())
    
    # Set Menu Button for Mini App
    # This button appears next to the message input field.
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Меню",
            web_app=WebAppInfo(url="https://gora.ru.net/menu")
        )
    )
    
    # Set bot commands (persistent menu)
    from aiogram.types import BotCommand
    await bot.set_my_commands([
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="help", description="❓ Помощь"),
        BotCommand(command="reload_content", description="🔄 Обновить контент (Админ)"),
    ])

    # Force-clear any stale Telegram sessions from previous crash loops
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Starting GORA Telegram bot")
    await dp.start_polling(bot, allowed_updates=['message', 'callback_query', 'inline_query'])


if __name__ == "__main__":
    init_db()
    asyncio.run(main())
