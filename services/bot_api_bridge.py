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
        self._order_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start polling for new admin messages and order notifications."""
        if self._running:
            return
        
        self._running = True
        self._running = True
        # self._task = asyncio.create_task(self._poll_messages())  # Disabled to prevent duplicates
        self._order_task = asyncio.create_task(self._poll_order_notifications())
        logger.info("Bot API Bridge started")
    
    async def stop(self):
        """Stop polling."""
        self._running = False
        for task in [self._order_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("Bot API Bridge stopped")
    
    async def _poll_order_notifications(self):
        """Poll for pending order notifications and send to users."""
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    async with session.get(f"{self.api_base}/pending-order-notifications") as response:
                        if response.status == 200:
                            notifications = await response.json()
                            
                            for notif in notifications:
                                telegram_id = notif.get("telegram_id")
                                if not telegram_id or telegram_id == "mini_app":
                                    continue
                                
                                try:
                                    # Build confirmation message
                                    msg = "✅ <b>Заказ оформлен!</b>\n\n"
                                    msg += f"<b>Заказ #{notif['ticket_id']}</b>\n"
                                    msg += f"👤 <b>Гость:</b> {notif['guest_name']}\n"
                                    msg += f"🏨 <b>Комната:</b> {notif['room_number']}\n\n"
                                    
                                    for item in notif.get("items", []):
                                        item_name = item.get('name', '')
                                        subtotal = item.get('subtotal', 0)
                                        qty = item.get('qty', 1)
                                        msg += f"🍽 <b>{item_name}</b> x{qty} = {subtotal}₽\n"
                                        
                                        composition = item.get("composition", [])
                                        if composition:
                                            comp_text = ", ".join(composition)
                                            msg += f"<i>   ({comp_text})</i>\n"
                                    
                                    msg += f"\n<b>💰 Итого: {notif['total']}₽</b>\n"
                                    
                                    if notif.get("comment"):
                                        msg += f"\n💬 Комментарий: {notif['comment']}\n"
                                    
                                    msg += "\nМы свяжемся с вами для уточнения времени доставки."
                                    
                                    await self.bot.send_message(
                                        chat_id=int(telegram_id),
                                        text=msg,
                                        parse_mode="HTML"
                                    )
                                    logger.info(f"Sent order notification to user {telegram_id}")
                                    
                                    # Mark as sent
                                    async with session.post(
                                        f"{self.api_base}/mark-notification-sent/{notif['ticket_id']}"
                                    ) as mark_resp:
                                        if mark_resp.status != 200:
                                            logger.error(f"Failed to mark notification as sent")
                                    
                                except Exception as e:
                                    logger.error(f"Failed to send order notification to {telegram_id}: {e}")
                    
                    # Check every 3 seconds
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.error(f"Error in order notification polling: {e}")
                    await asyncio.sleep(10)
    
    async def _poll_messages(self):
        """Poll for new admin messages and deliver them to users."""
        last_checked_message_id = 0
        
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    # Check for new admin messages
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
                                                
                                                chat_id_str = ticket.get('guest_chat_id', '')
                                                if not chat_id_str or not chat_id_str.isdigit():
                                                    last_checked_message_id = max(last_checked_message_id, message['id'])
                                                    continue
                                                
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
