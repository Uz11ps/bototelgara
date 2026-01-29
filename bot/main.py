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
from services.bot_api_bridge import get_bot_bridge


logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    if not settings.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    register_handlers(dp)
    
    # Start bot API bridge for delivering admin messages
    bridge = get_bot_bridge(bot)
    await bridge.start()
    
    # Set Menu Button for Mini App
    # NOTE: Telegram requires a PUBLIC HTTPS URL. localhost will not work here.
    # To enable, replace the URL with your public HTTPS URL (e.g., from GitHub Pages or Vercel)
    # await bot.set_chat_menu_button(
    #     menu_button=MenuButtonWebApp(
    #         text="Меню",
    #         web_app=WebAppInfo(url="YOUR_PUBLIC_HTTPS_URL_HERE")
    #     )
    # )

    logger.info("Starting GORA Telegram bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    init_db()
    asyncio.run(main())
