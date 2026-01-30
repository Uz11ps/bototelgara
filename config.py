import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    bot_token: str | None
    database_url: str
    admin_registration_token: str | None
    log_level: str


def get_settings() -> Settings:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    database_url = os.getenv("DATABASE_URL", "sqlite:///./gora_bot.db")
    
    if database_url.startswith('"') and database_url.endswith('"'):
        database_url = database_url[1:-1]
    
    print(f"DEBUG: Using database URL: {database_url}")
    admin_registration_token = os.getenv("ADMIN_REGISTRATION_TOKEN")
    log_level = os.getenv("LOG_LEVEL", "INFO")

    # Do not log secrets
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    return Settings(
        bot_token=bot_token,
        database_url=database_url,
        admin_registration_token=admin_registration_token,
        log_level=log_level,
    )
