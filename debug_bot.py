import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.main import register_handlers
from bot.handlers import reply_nav, booking, pre_arrival, check_in

# Mock settings
class Settings:
    bot_token = "123:fake"

async def main():
    print("Checking router registration...")
    dp = Dispatcher(storage=MemoryStorage())
    
    # Simulate main.py registration
    from bot.middleware import ThrottlingMiddleware, CallbackAnswerMiddleware
    dp.callback_query.middleware(ThrottlingMiddleware(throttle_time=0.25))
    dp.callback_query.middleware(CallbackAnswerMiddleware())

    dp.include_router(reply_nav.router)
    register_handlers(dp)
    
    print(f"Total routers: {len(dp.sub_routers)}")
    
    for i, router in enumerate(dp.sub_routers):
        name = "Unknown"
        if router == reply_nav.router: name = "reply_nav"
        elif router == booking.router: name = "booking"
        elif router == pre_arrival.router: name = "pre_arrival"
        elif router == check_in.router: name = "check_in"
        # ... add others if needed
        
        print(f"Router {i}: {name} (Handlers: {len(router.message.handlers) + len(router.callback_query.handlers)})")
        
        # Check specific handlers
        for handler in router.callback_query.handlers:
            print(f"  - Handler: {handler.callback}")
            print(f"    Filters: {handler.filters}")

if __name__ == "__main__":
    import sys
    # Mock config to avoid error
    sys.modules['config'] = type('config', (), {'get_settings': lambda: Settings()})
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
