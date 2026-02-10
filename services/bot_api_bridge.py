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
        self._task = asyncio.create_task(self._poll_messages())
        self._order_task = asyncio.create_task(self._poll_order_notifications())
        logger.info("Bot API Bridge started")
    
    async def stop(self):
        """Stop polling."""
        self._running = False
        for task in [self._task, self._order_task]:
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
                                if not telegram_id or not str(telegram_id).isdigit():
                                    # Mark as sent so it doesn't retry forever
                                    try:
                                        async with session.post(
                                            f"{self.api_base}/mark-notification-sent/{notif['ticket_id']}"
                                        ) as _:
                                            pass
                                    except Exception:
                                        pass
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
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in order notification polling: {e}")
                    await asyncio.sleep(10)
    
    async def _poll_messages(self):
        """Poll for undelivered admin messages and deliver them to users."""
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    async with session.get(f"{self.api_base}/undelivered-admin-messages") as response:
                        if response.status == 200:
                            messages = await response.json()
                            
                            for msg in messages:
                                message_id = msg.get("message_id")
                                guest_chat_id = msg.get("guest_chat_id")
                                
                                if not guest_chat_id or not str(guest_chat_id).isdigit():
                                    # Mark as delivered so it doesn't retry
                                    async with session.post(
                                        f"{self.api_base}/mark-message-delivered/{message_id}"
                                    ) as _:
                                        pass
                                    continue
                                
                                try:
                                    admin_name = msg.get("admin_name", "Администратор")
                                    ticket_id = msg.get("ticket_id")
                                    message_text = (
                                        f"\U0001f4ac Ответ от {admin_name} по заявке #{ticket_id}:\n\n"
                                        f"{msg['content']}"
                                    )
                                    
                                    await self.bot.send_message(
                                        chat_id=int(guest_chat_id),
                                        text=message_text
                                    )
                                    logger.info(
                                        f"Delivered admin message {message_id} "
                                        f"from {admin_name} to user {guest_chat_id}"
                                    )
                                    
                                    # Mark as delivered in DB
                                    async with session.post(
                                        f"{self.api_base}/mark-message-delivered/{message_id}"
                                    ) as mark_resp:
                                        if mark_resp.status != 200:
                                            logger.error(f"Failed to mark message {message_id} as delivered")
                                    
                                except Exception as e:
                                    logger.error(
                                        f"Failed to deliver message {message_id} to user "
                                        f"{guest_chat_id}: {e}"
                                    )
                        else:
                            logger.warning(f"Admin messages poll returned status {response.status}")
                    
                    # Check every 5 seconds
                    await asyncio.sleep(5)
                    
                except asyncio.CancelledError:
                    raise
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
