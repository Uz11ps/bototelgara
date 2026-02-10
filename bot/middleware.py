"""
Middleware for the Telegram bot.
Provides throttling and other cross-cutting concerns.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware to prevent rapid duplicate button clicks.
    
    If a user clicks buttons faster than the specified interval,
    the middleware will:
    1. Immediately acknowledge the callback to prevent "loading" spinner
    2. Skip processing the handler
    
    This prevents the bot from hanging when users rapidly click buttons.
    """
    
    def __init__(self, throttle_time: float = 0.1):
        """
        Initialize throttling middleware.
        
        Args:
            throttle_time: Minimum time (seconds) between callback processing for same user.
        """
        super().__init__()
        self.throttle_time = throttle_time
        self._last_callback: Dict[int, float] = {}
        self._locks: Dict[int, asyncio.Lock] = {}
    
    def _get_lock(self, user_id: int) -> asyncio.Lock:
        """Get or create a lock for a user."""
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Only throttle callback queries
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        
        user_id = event.from_user.id
        current_time = time.monotonic()
        
        # Use lock to prevent race conditions
        lock = self._get_lock(user_id)
        
        async with lock:
            last_time = self._last_callback.get(user_id, 0)
            time_diff = current_time - last_time
            
            if time_diff < self.throttle_time:
                # Too fast! Acknowledge but skip processing
                try:
                    await event.answer()
                except Exception:
                    pass
                return None
            
            # Update last callback time
            self._last_callback[user_id] = current_time
        
        # Process the handler
        return await handler(event, data)


class CallbackAnswerMiddleware(BaseMiddleware):
    """
    Middleware that ensures callback queries are always answered.
    
    This prevents the "clock" spinner from appearing if a handler
    forgets to call callback.answer() or crashes before doing so.
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)
        
        try:
            result = await handler(event, data)
        finally:
            # Always try to answer the callback, even if handler crashed
            try:
                if not event.answered:
                    await event.answer()
            except Exception:
                pass
        
        return result
