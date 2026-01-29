"""
Service for integrating bot with web admin API.
Handles delivering admin messages to users via Telegram.
"""
import asyncio
import logging
from typing import Optional

import aiohttp
from aiogram import Bot

from config import get_settings

logger = logging.getLogger(__name__)


class BotAPIBridge:
    """Bridge between FastAPI admin panel and Telegram bot."""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.settings = get_settings()
        self.api_base = "http://localhost:8000/api"
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start polling for new admin messages."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._poll_messages())
        logger.info("Bot API Bridge started")
    
    async def stop(self):
        """Stop polling."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Bot API Bridge stopped")
    
    async def _poll_messages(self):
        """Poll for new admin messages and deliver them to users."""
        last_checked_message_id = 0
        
        while self._running:
            try:
                # Check for new admin messages
                async with aiohttp.ClientSession() as session:
                    # Get all tickets with recent admin messages
                    async with session.get(f"{self.api_base}/tickets") as response:
                        if response.status == 200:
                            tickets = await response.json()
                            
                            for ticket in tickets:
                                # Get ticket details with messages
                                async with session.get(
                                    f"{self.api_base}/tickets/{ticket['id']}"
                                ) as detail_response:
                                    if detail_response.status == 200:
                                        ticket_detail = await detail_response.json()
                                        
                                        # Check for undelivered admin messages
                                        for message in ticket_detail.get('messages', []):
                                            if (message['sender'] == 'ADMIN' and 
                                                message['id'] > last_checked_message_id):
                                                
                                                # Send to user
                                                try:
                                                    # Format message with admin name if available
                                                    admin_name = message.get('admin_name', 'Администратор')
                                                    message_text = (
                                                        f"💬 Ответ от {admin_name} по заявке #{ticket['id']}:\n\n"
                                                        f"{message['content']}"
                                                    )
                                                    
                                                    await self.bot.send_message(
                                                        chat_id=int(ticket['guest_chat_id']),
                                                        text=message_text
                                                    )
                                                    logger.info(
                                                        f"Delivered admin message {message['id']} "
                                                        f"from {admin_name} to user {ticket['guest_chat_id']}"
                                                    )
                                                    last_checked_message_id = max(
                                                        last_checked_message_id, 
                                                        message['id']
                                                    )
                                                except Exception as e:
                                                    logger.error(
                                                        f"Failed to deliver message to user "
                                                        f"{ticket['guest_chat_id']}: {e}"
                                                    )
                
                # Check every 5 seconds
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in message polling: {e}")
                await asyncio.sleep(10)


# Global bridge instance
_bridge: Optional[BotAPIBridge] = None


def get_bot_bridge(bot: Bot) -> BotAPIBridge:
    """Get or create the bot API bridge."""
    global _bridge
    if _bridge is None:
        _bridge = BotAPIBridge(bot)
    return _bridge
