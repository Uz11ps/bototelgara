import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import register_handlers
from config import get_settings

async def main():
    print("Initializing bot...")
    dp = Dispatcher(storage=MemoryStorage())
    
    print("Registering handlers...")
    try:
        register_handlers(dp)
        print("Handlers registered successfully!")
    except Exception as e:
        print(f"Error registering handlers: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
