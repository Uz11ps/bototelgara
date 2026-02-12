"""
FastAPI web admin panel for managing hotel tickets.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import asyncio
from sqlalchemy.orm import Session

import aiohttp
import yaml

from db.models import Ticket, TicketMessage, TicketMessageSender, TicketStatus, TicketType, MenuItem, GuideItem, StaffTask, User, Staff, StaffRole, GuestBooking, CleaningRequest, MenuCategory, AdminUser
from db.session import SessionLocal
from services.shelter import get_shelter_client, ShelterAPIError
from config import get_settings


logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = PROJECT_ROOT / "content"
MENUS_PATH = CONTENT_DIR / "menus.ru.yml"
REPLY_BUTTONS_PATH = CONTENT_DIR / "reply_buttons.ru.yml"

# --- Direct Telegram Bot API helper ---
_settings = get_settings()
TELEGRAM_BOT_TOKEN = _settings.bot_token
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage" if TELEGRAM_BOT_TOKEN else None


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message directly via Telegram Bot API. Returns True on success."""
    if not TELEGRAM_API_URL:
        logger.error("TELEGRAM_BOT_TOKEN not set, can't send message")
        return False
    if not chat_id or not chat_id.isdigit():
        logger.warning(f"Invalid chat_id '{chat_id}', can't send message")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(TELEGRAM_API_URL, json={
                "chat_id": int(chat_id),
                "text": text,
                "parse_mode": parse_mode,
            }) as resp:
                result = await resp.json()
                if result.get("ok"):
                    logger.info(f"Telegram message sent to {chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error: {result}")
                    return False
    except Exception as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        return False
app = FastAPI(title="GORA Hotel Admin API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://gora.ru.net", "https://gora.ru.net", "http://89.104.66.21", "https://89.104.66.21"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models
class TicketResponse(BaseModel):
    id: int
    type: str
    status: str
    guest_chat_id: str
    guest_name: Optional[str]
    room_number: Optional[str]
    created_at: datetime
    updated_at: datetime


def _read_yaml_file(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"Invalid YAML structure: {path.name}")
    return data


def _write_yaml_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    sender: str
    content: str
    created_at: datetime
    admin_telegram_id: Optional[str] = None
    admin_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TicketDetailResponse(TicketResponse):
    messages: List[MessageResponse]
    payload: Optional[dict]


class SendMessageRequest(BaseModel):
    content: str
    admin_telegram_id: Optional[str] = None
    admin_name: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


class StatisticsResponse(BaseModel):
    total_tickets_today: int
    pending_tickets: int
    completed_today: int
    declined_today: int
    total_active: int


# API Routes
@app.get("/api")
async def root_api():
    return {"message": "GORA Hotel Admin API", "version": "1.0.0"}


@app.get("/api/tickets", response_model=List[TicketResponse])
async def get_all_tickets(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all tickets, optionally filtered by status."""
    query = db.query(Ticket)
    
    if status:
        try:
            status_enum = TicketStatus(status)
            query = query.filter(Ticket.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_detail(ticket_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific ticket."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket


@app.post("/api/tickets/{ticket_id}/messages", response_model=MessageResponse)
async def send_message_to_ticket(
    ticket_id: int,
    message_request: SendMessageRequest,
    db: Session = Depends(get_db)
):
    """Send a message from admin to a ticket (will be delivered to user via bot)."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Create message
    from uuid import uuid4
    message = TicketMessage(
        ticket_id=ticket_id,
        sender=TicketMessageSender.ADMIN,
        content=message_request.content,
        request_id=str(uuid4()),
        admin_telegram_id=message_request.admin_telegram_id,
        admin_name=message_request.admin_name
    )
    
    db.add(message)
    db.commit()
    db.refresh(message)
    
    # Directly deliver admin reply to user via Telegram Bot API
    chat_id = ticket.guest_chat_id
    if chat_id and chat_id.isdigit():
        admin_name = message_request.admin_name or "Администратор"
        tg_text = (
            f"💬 Ответ от {admin_name} по заявке #{ticket_id}:\n\n"
            f"{message_request.content}"
        )
        sent = await send_telegram_message(chat_id, tg_text)
        if sent:
            logger.info(f"Admin reply delivered to user {chat_id} for ticket #{ticket_id}")
        else:
            logger.warning(f"Could not deliver admin reply to user {chat_id} for ticket #{ticket_id}")
    else:
        logger.warning(f"Ticket #{ticket_id} has no valid guest_chat_id ({chat_id}), can't deliver reply")
    
    return message


@app.patch("/api/tickets/{ticket_id}/status")
async def update_ticket_status(
    ticket_id: int,
    status_request: UpdateStatusRequest,
    db: Session = Depends(get_db)
):
    """Update ticket status (e.g., mark as completed or declined)."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    try:
        new_status = TicketStatus(status_request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status_request.status}")
    
    ticket.status = new_status
    ticket.updated_at = datetime.utcnow()
    db.commit()
    
    # Send notification to user via Telegram
    try:
        from services.content import content_manager
        if new_status == TicketStatus.COMPLETED:
            notification_text = content_manager.get_text("tickets.resolved").format(ticket_id=ticket_id)
        elif new_status == TicketStatus.DECLINED:
            notification_text = content_manager.get_text("tickets.declined").format(ticket_id=ticket_id)
        else:
            notification_text = None
        
        if notification_text:
            # The bot bridge will pick this up and send to user
            # Or we can directly call the bot here (requires bot instance)
            pass
    except Exception as e:
        logger.error(f"Failed to prepare notification: {e}")
    
    return {"message": f"Ticket #{ticket_id} status updated to {new_status.value}"}


@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get statistics for today."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_tickets_today = db.query(Ticket).filter(
        Ticket.created_at >= today_start
    ).count()
    
    pending_tickets = db.query(Ticket).filter(
        Ticket.status.in_([TicketStatus.NEW, TicketStatus.PENDING_ADMIN])
    ).count()
    
    completed_today = db.query(Ticket).filter(
        Ticket.status == TicketStatus.COMPLETED,
        Ticket.updated_at >= today_start
    ).count()
    
    declined_today = db.query(Ticket).filter(
        Ticket.status == TicketStatus.DECLINED,
        Ticket.updated_at >= today_start
    ).count()
    
    total_active = db.query(Ticket).filter(
        Ticket.status.in_([TicketStatus.NEW, TicketStatus.PENDING_ADMIN])
    ).count()
    
    return StatisticsResponse(
        total_tickets_today=total_tickets_today,
        pending_tickets=pending_tickets,
        completed_today=completed_today,
        declined_today=declined_today,
        total_active=total_active
    )


@app.get("/api/shelter/hotel-params")
async def get_shelter_hotel_params():
    """Get hotel parameters from Shelter API."""
    try:
        shelter = get_shelter_client()
        return await shelter.get_hotel_params()
    except ShelterAPIError as e:
        raise HTTPException(status_code=500, detail=f"Shelter API error: {e.message}")


@app.get("/api/shelter/order/{order_token}")
async def get_shelter_order(order_token: str):
    """Get order details from Shelter API."""
    try:
        shelter = get_shelter_client()
        return await shelter.get_order(order_token)
    except ShelterAPIError as e:
        raise HTTPException(status_code=500, detail=f"Shelter API error: {e.message}")


@app.get("/api/shelter/availability")
async def get_shelter_availability(
    check_in: str,
    check_out: str,
    adults: int = 1
):
    """Get room availability for specific dates."""
    try:
        from datetime import datetime
        from dataclasses import asdict
        ci = datetime.strptime(check_in, "%Y-%m-%d").date()
        co = datetime.strptime(check_out, "%Y-%m-%d").date()
        shelter = get_shelter_client()
        variants = await shelter.get_variants(ci, co, adults)
        # Ensure we return a list of dicts
        return [asdict(v) if hasattr(v, '__dataclass_fields__') else v for v in variants]
    except Exception as e:
        logger.error(f"Availability error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# --- Content Management Endpoints ---

@app.get("/api/menu")
async def get_menu(db: Session = Depends(get_db)):
    return db.query(MenuItem).all()

@app.post("/api/menu")
async def create_menu_item(item: dict, db: Session = Depends(get_db)):
    # Handle category_type enum
    if "category_type" in item and isinstance(item["category_type"], str):
        item["category_type"] = MenuCategory(item["category_type"])
    new_item = MenuItem(**item)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/menu/{item_id}")
async def update_menu_item(item_id: int, item_data: dict, db: Session = Depends(get_db)):
    """Update a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    # Update fields
    for key, value in item_data.items():
        if key == "category_type" and isinstance(value, str):
            value = MenuCategory(value)
        if hasattr(item, key):
            setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/menu/{item_id}")
async def delete_menu_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a menu item."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    db.delete(item)
    db.commit()
    return {"message": f"Menu item {item_id} deleted"}

@app.patch("/api/menu/{item_id}/toggle")
async def toggle_menu_item(item_id: int, db: Session = Depends(get_db)):
    """Toggle menu item availability."""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    item.is_available = not item.is_available
    db.commit()
    return {"is_available": item.is_available}

@app.get("/api/guide")
async def get_guide(db: Session = Depends(get_db)):
    return db.query(GuideItem).all()

@app.post("/api/guide")
async def create_guide_item(item: dict, db: Session = Depends(get_db)):
    """Create a new guide item."""
    new_item = GuideItem(**item)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item

@app.put("/api/guide/{item_id}")
async def update_guide_item(item_id: int, item_data: dict, db: Session = Depends(get_db)):
    """Update a guide item."""
    item = db.query(GuideItem).filter(GuideItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Guide item not found")
    
    for key, value in item_data.items():
        if hasattr(item, key):
            setattr(item, key, value)
    
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/guide/{item_id}")
async def delete_guide_item(item_id: int, db: Session = Depends(get_db)):
    """Delete a guide item."""
    item = db.query(GuideItem).filter(GuideItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Guide item not found")
    
    db.delete(item)
    db.commit()
    return {"message": f"Guide item {item_id} deleted"}


@app.get("/api/content/button-texts")
async def get_button_texts():
    """Return editable bot button texts for admin panel."""
    return {
        "reply_buttons": _read_yaml_file(REPLY_BUTTONS_PATH),
        "menus": _read_yaml_file(MENUS_PATH),
    }


@app.put("/api/content/button-texts")
async def update_button_texts(payload: dict):
    """Update editable button texts and reload content cache."""
    reply_buttons = payload.get("reply_buttons")
    menus = payload.get("menus")
    if not isinstance(reply_buttons, dict) or not isinstance(menus, dict):
        raise HTTPException(status_code=400, detail="reply_buttons and menus must be objects")

    _write_yaml_file(REPLY_BUTTONS_PATH, reply_buttons)
    _write_yaml_file(MENUS_PATH, menus)

    from services.content import content_manager

    content_manager.reload()
    return {"status": "ok"}

@app.get("/api/staff/tasks")
async def get_staff_tasks(db: Session = Depends(get_db)):
    return db.query(StaffTask).order_by(StaffTask.created_at.desc()).all()

@app.post("/api/staff/tasks")
async def create_staff_task(task: dict, db: Session = Depends(get_db)):
    try:
        # Handle scheduled_at
        if "scheduled_at" in task and task["scheduled_at"]:
            try:
                # Ensure valid ISO format
                 dt = datetime.fromisoformat(task["scheduled_at"].replace("Z", "+00:00"))
                 # Keep local naive datetime (server local time, MSK)
                 if dt.tzinfo is not None:
                     dt = dt.astimezone().replace(tzinfo=None)
                 task["scheduled_at"] = dt
            except ValueError as e:
                logger.error(f"Invalid date format: {task['scheduled_at']} - {e}")
                task["scheduled_at"] = None
        else:
            task["scheduled_at"] = None
        
        # Ensure assigned_to is normalized to staff telegram_id
        if "assigned_to" in task and task["assigned_to"]:
            raw_assigned_to = str(task["assigned_to"]).strip()
            staff = db.query(Staff).filter(Staff.telegram_id == raw_assigned_to).first()
            if not staff and raw_assigned_to.isdigit():
                # Backward compatibility: UI or old data can send staff.id
                staff = db.query(Staff).filter(Staff.id == int(raw_assigned_to)).first()
            if not staff or not staff.telegram_id:
                raise HTTPException(status_code=400, detail="У сотрудника не указан корректный Telegram ID")
            task["assigned_to"] = str(staff.telegram_id)
        else:
            task["assigned_to"] = None

        new_task = StaffTask(**task)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        # Send notification to assigned staff member immediately
        if new_task.assigned_to:
            try:
                # Find staff member by telegram_id
                staff = db.query(Staff).filter(Staff.telegram_id == new_task.assigned_to).first()
                if staff and staff.telegram_id:
                    # Build notification message
                    msg = "📋 <b>Новая задача назначена</b>\n\n"
                    msg += f"🏨 <b>Комната:</b> {new_task.room_number}\n"
                    msg += f"📌 <b>Тип:</b> {new_task.task_type}\n"
                    if new_task.scheduled_at:
                        msg += f"🕒 <b>Запланировано на:</b> {new_task.scheduled_at.strftime('%d.%m.%Y %H:%M')}\n"
                    if new_task.description:
                        msg += f"\n📝 <b>Описание:</b>\n{new_task.description}\n"
                    msg += f"\n🆔 <b>ID задачи:</b> #{new_task.id}"
                    
                    # Send via Telegram Bot API
                    sent = await send_telegram_message(staff.telegram_id, msg)
                    if sent:
                        logger.info(f"Task notification sent to staff {staff.full_name} (telegram_id: {staff.telegram_id}) for task #{new_task.id}")
                    else:
                        logger.warning(f"Failed to send task notification to staff {staff.full_name} (telegram_id: {staff.telegram_id})")
                else:
                    logger.warning(f"Staff member with telegram_id {new_task.assigned_to} not found or has no telegram_id")
            except Exception as e:
                logger.error(f"Error sending task notification: {e}")
                # Don't fail task creation if notification fails
        
        return new_task
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@app.post("/api/staff/tasks/{task_id}/complete")
async def complete_staff_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if task:
        task.status = "COMPLETED"
        task.completed_at = datetime.utcnow()
        db.commit()
    return {"status": "ok"}

@app.delete("/api/staff/tasks/{task_id}")
async def delete_staff_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db.delete(task)
    db.commit()
    return {"message": f"Task {task_id} deleted"}

# --- Staff Management Endpoints ---

@app.get("/api/staff")
async def get_all_staff(db: Session = Depends(get_db)):
    """Get all staff members."""
    return db.query(Staff).all()

@app.get("/api/staff/me")
async def get_staff_by_identifier(telegram_id: str = None, phone: str = None, db: Session = Depends(get_db)):
    """Get staff member by Telegram ID or phone number."""
    staff = None
    if telegram_id:
        staff = db.query(Staff).filter(Staff.telegram_id == telegram_id).first()
    if not staff and phone:
        staff = db.query(Staff).filter(Staff.phone == phone).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    return staff

@app.post("/api/staff")
async def create_staff(staff_data: dict, db: Session = Depends(get_db)):
    """Create a new staff member."""
    # Convert role string to enum
    if "role" in staff_data and isinstance(staff_data["role"], str):
        staff_data["role"] = StaffRole(staff_data["role"])
    
    new_staff = Staff(**staff_data)
    db.add(new_staff)
    db.commit()
    db.refresh(new_staff)
    return new_staff

@app.put("/api/staff/{staff_id}")
async def update_staff(staff_id: int, staff_data: dict, db: Session = Depends(get_db)):
    """Update a staff member."""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    for key, value in staff_data.items():
        if key == "role" and isinstance(value, str):
            value = StaffRole(value)
        if hasattr(staff, key):
            setattr(staff, key, value)
    
    db.commit()
    db.refresh(staff)
    return staff

@app.delete("/api/staff/{staff_id}")
async def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    """Delete a staff member."""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    db.delete(staff)
    db.commit()
    return {"message": f"Staff {staff_id} deleted"}

@app.patch("/api/staff/{staff_id}/permissions")
async def update_staff_permissions(staff_id: int, permissions: dict, db: Session = Depends(get_db)):
    """Update staff permissions."""
    staff = db.query(Staff).filter(Staff.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")
    
    staff.permissions = permissions
    db.commit()
    return {"permissions": staff.permissions}

@app.get("/api/users")
async def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@app.get("/api/check-admin")
async def check_admin(telegram_id: str, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.telegram_id == telegram_id, AdminUser.is_active == True).first()
    return {"is_admin": admin is not None}


@app.post("/api/marketing/broadcast")
async def broadcast_message(data: dict):
    # In a real app, this would trigger a background task to send messages via bot
    return {"message": f"Рассылка '{data['text']}' запланирована для {data['target']} пользователей"}


# --- Guest Order Endpoint ---

class GuestOrderRequest(BaseModel):
    guest_name: str
    room_number: str
    comment: Optional[str] = None
    items: List[dict]  # [{id: 1, qty: 1}, ...]
    telegram_id: Optional[str] = None  # Telegram user ID for notifications

@app.post("/api/orders")
async def create_guest_order(order: GuestOrderRequest, db: Session = Depends(get_db)):
    """Create a new guest order from mini app."""
    logger.info(f"Received order: guest={order.guest_name}, room={order.room_number}, telegram_id={order.telegram_id}, items={len(order.items)}")
    
    # Get menu items and calculate total
    cart_items = []
    total = 0
    order_lines = []
    
    for order_item in order.items:
        item = db.query(MenuItem).filter(MenuItem.id == order_item.get("id")).first()
        if item:
            qty = order_item.get("qty", 1)
            cart_items.append({"item": item, "qty": qty})
            total += item.price * qty
            
            # Build composition string for summary
            comp_list = []
            if item.composition and isinstance(item.composition, list):
                for c in item.composition:
                    c_name = c.get("name", "")
                    if c.get("quantity") and c.get("unit"):
                        c_name += f" ({c['quantity']} {c['unit']})"
                    comp_list.append(c_name)
            
            comp_str = f" [{', '.join(comp_list)}]" if comp_list else ""
            order_lines.append(f"{item.name}{comp_str} x{qty} = {item.price * qty}₽")
    
    if not cart_items:
        raise HTTPException(status_code=400, detail="No valid items in order")
    
    # Create ticket
    from uuid import uuid4
    from services.tickets import create_ticket
    
    payload = {
        "branch": "mini_app_order",
        "items": [{
            "id": ci["item"].id,
            "name": ci["item"].name,
            "qty": ci["qty"],
            "price": ci["item"].price,
            "subtotal": ci["item"].price * ci["qty"],
            "composition": [c.get("name", "") for c in (ci["item"].composition or []) if isinstance(c, dict)]
        } for ci in cart_items],
        "total": total,
        "guest_name": order.guest_name,
        "room_number": order.room_number,
        "guest_comment": order.comment or "",
    }
    
    summary = f"Заказ из Mini App:\nГость: {order.guest_name}\nКомната: {order.room_number}\n\n" + "\n".join(order_lines) + f"\nИтого: {total}₽"
    if order.comment:
        summary += f"\nКомментарий: {order.comment}"
    
    ticket = Ticket(
        request_id=str(uuid4()),
        type=TicketType.MENU_ORDER,
        status=TicketStatus.PENDING_ADMIN,
        guest_chat_id=order.telegram_id or "mini_app",
        guest_name=order.guest_name,
        room_number=order.room_number,
        payload=payload,
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    logger.info(f"Created ticket #{ticket.id} for guest_chat_id={ticket.guest_chat_id}, type={ticket.type}")
    
    # Add initial message
    message = TicketMessage(
        ticket_id=ticket.id,
        request_id=str(uuid4()),
        sender=TicketMessageSender.GUEST,
        content=summary,
    )
    db.add(message)
    db.commit()
    
    # --- Direct Telegram notification to user ---
    if order.telegram_id and order.telegram_id.isdigit():
        notif_msg = "✅ <b>Заказ оформлен!</b>\n\n"
        notif_msg += f"<b>Заказ #{ticket.id}</b>\n"
        notif_msg += f"👤 <b>Гость:</b> {order.guest_name}\n"
        notif_msg += f"🏨 <b>Комната:</b> {order.room_number}\n\n"
        
        for ci in cart_items:
            item = ci["item"]
            qty = ci["qty"]
            subtotal = item.price * qty
            notif_msg += f"🍽 <b>{item.name}</b> x{qty} = {subtotal}₽\n"
        
        notif_msg += f"\n<b>💰 Итого: {total}₽</b>\n"
        if order.comment:
            notif_msg += f"\n💬 Комментарий: {order.comment}\n"
        notif_msg += "\nМы свяжемся с вами для уточнения времени доставки."
        
        sent = await send_telegram_message(order.telegram_id, notif_msg)
        if sent:
            # Mark as notified immediately
            payload_copy = dict(ticket.payload or {})
            payload_copy["guest_notified"] = True
            ticket.payload = payload_copy
            db.commit()
            logger.info(f"Order notification sent directly to user {order.telegram_id} for ticket #{ticket.id}")
        else:
            logger.warning(f"Could not send order notification to user {order.telegram_id}")
    
    # --- Notify admins about new order ---
    admins = db.query(AdminUser).filter(AdminUser.is_active == True).all()
    admin_msg = f"📦 <b>Новый заказ #{ticket.id}</b>\n\n"
    admin_msg += f"👤 Гость: {order.guest_name}\n"
    admin_msg += f"🏨 Комната: {order.room_number}\n\n"
    for ci in cart_items:
        item = ci["item"]
        qty = ci["qty"]
        admin_msg += f"🍽 {item.name} x{qty} = {item.price * qty}₽\n"
    admin_msg += f"\n<b>💰 Итого: {total}₽</b>"
    if order.comment:
        admin_msg += f"\n💬 {order.comment}"
    
    for admin in admins:
        await send_telegram_message(admin.telegram_id, admin_msg)
    
    # Build response with composition
    response_items = []
    for ci in cart_items:
        item = ci["item"]
        item_data = {
            "name": item.name,
            "qty": ci["qty"],
            "price": item.price,
            "subtotal": item.price * ci["qty"],
            "composition": []
        }
        if item.composition and isinstance(item.composition, list):
            for comp in item.composition:
                comp_str = comp.get("name", "")
                if comp.get("quantity") and comp.get("unit"):
                    comp_str += f" - {comp['quantity']} {comp['unit']}"
                item_data["composition"].append(comp_str)
        response_items.append(item_data)
    
    return {
        "success": True,
        "order_id": ticket.id,
        "guest_name": order.guest_name,
        "room_number": order.room_number,
        "items": response_items,
        "total": total,
        "message": "Заказ успешно оформлен!",
        "telegram_id": order.telegram_id  # Return for notification
    }


# --- Pending Order Notifications ---

@app.get("/api/pending-order-notifications")
async def get_pending_order_notifications(db: Session = Depends(get_db)):
    """Get orders that need Telegram notification to guest."""
    # Find recent MENU_ORDER tickets with telegram_id that haven't been notified
    from datetime import datetime, timedelta
    
    recent_time = datetime.utcnow() - timedelta(minutes=10)  # Only check last 10 minutes
    
    tickets = db.query(Ticket).filter(
        Ticket.type == TicketType.MENU_ORDER,
        Ticket.created_at >= recent_time,
        Ticket.guest_chat_id != "mini_app",  # Has telegram_id
    ).all()
    
    logger.info(f"Found {len(tickets)} recent MENU_ORDER tickets (last 10 min, guest_chat_id != 'mini_app')")
    
    notifications = []
    for ticket in tickets:
        # Check if notification was already sent (tracked in payload)
        payload = ticket.payload or {}
        if payload.get("guest_notified"):
            logger.info(f"Ticket #{ticket.id} already notified, skipping")
            continue
        
        logger.info(f"Preparing notification for ticket #{ticket.id}, guest_chat_id={ticket.guest_chat_id}")
        
        # Build notification data
        items_data = payload.get("items", [])
        total = payload.get("total", 0)
        
        notifications.append({
            "ticket_id": ticket.id,
            "telegram_id": ticket.guest_chat_id,
            "guest_name": ticket.guest_name,
            "room_number": ticket.room_number,
            "items": items_data,
            "total": total,
            "comment": payload.get("guest_comment", "")
        })
    
    logger.info(f"Returning {len(notifications)} pending notifications")
    return notifications


@app.post("/api/mark-notification-sent/{ticket_id}")
async def mark_notification_sent(ticket_id: int, db: Session = Depends(get_db)):
    """Mark order notification as sent to guest."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Update payload to mark as notified
    payload = dict(ticket.payload or {})
    payload["guest_notified"] = True
    ticket.payload = payload
    db.commit()
    
    return {"success": True}


# --- Camera Streaming Endpoints ---

CAMERA_URLS = {
    "camera1": "rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/0",
    "camera2": "rtsp://Sayt:pDA11BkIcwXuKK3@78.36.41.145:8282/1",
}

async def generate_mjpeg_stream(camera_id: str):
    """Generate MJPEG stream from RTSP using ffmpeg."""
    rtsp_url = CAMERA_URLS.get(camera_id)
    if not rtsp_url:
        return
    
    # FFmpeg command to convert RTSP to MJPEG
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-f", "mjpeg",
        "-q:v", "5",
        "-r", "10",  # 10 fps
        "-s", "640x360",  # Resolution
        "-an",  # No audio
        "pipe:1"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        
        while True:
            # Read MJPEG frame
            chunk = await process.stdout.read(8192)
            if not chunk:
                break
            yield chunk
            
    except Exception as e:
        logger.error(f"Camera stream error: {e}")
    finally:
        if process:
            process.kill()


@app.get("/api/camera/{camera_id}/stream")
async def get_camera_stream(camera_id: str):
    """Stream camera as MJPEG."""
    if camera_id not in CAMERA_URLS:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return StreamingResponse(
        generate_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/camera/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str):
    """Get a single snapshot from camera."""
    rtsp_url = CAMERA_URLS.get(camera_id)
    if not rtsp_url:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # FFmpeg command to capture single frame
    cmd = [
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-vframes", "1",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-s", "640x360",
        "pipe:1"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
        
        if stdout:
            return StreamingResponse(
                iter([stdout]),
                media_type="image/jpeg",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to capture snapshot")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Camera timeout")
    except Exception as e:
        logger.error(f"Snapshot error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cameras")
async def get_cameras_info():
    """Get list of available cameras."""
    return [
        {"id": "camera1", "name": "Камера 1", "rtsp_url": CAMERA_URLS["camera1"]},
        {"id": "camera2", "name": "Камера 2", "rtsp_url": CAMERA_URLS["camera2"]},
    ]


# Serve static files from admin_panel directory
admin_panel_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_panel")
mini_app_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mini_app")

if os.path.exists(admin_panel_path):
    @app.get("/admin")
    async def serve_admin():
        return FileResponse(os.path.join(admin_panel_path, "index.html"))

# Serve mini app for guests (React build)
react_build_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mini_app")
if os.path.exists(react_build_path):
    @app.get("/menu")
    async def serve_mini_app():
        index_path = os.path.join(react_build_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(
                index_path,
                headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
            )
        else:
            # Fallback to old mini_app/index.html if React build not found
            old_path = os.path.join(react_build_path, "index.html")
            if os.path.exists(old_path):
                return FileResponse(old_path)
            raise HTTPException(status_code=404, detail="Mini app not found")
    
    # Serve static assets from React build with no-cache headers
    from fastapi.responses import FileResponse
    
    @app.get("/assets/{file_path:path}")
    async def serve_react_assets(file_path: str):
        """Serve React build assets with no-cache headers."""
        asset_path = os.path.join(react_build_path, "assets", file_path)
        if os.path.exists(asset_path):
            return FileResponse(
                asset_path,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        raise HTTPException(status_code=404)
    
    app.mount("/mini_app", StaticFiles(directory=react_build_path, html=True), name="mini_app")

# Mount admin panel static files at the root. 
# MUST be the last route defined to avoid shadowing API routes.
if os.path.exists(admin_panel_path):
    app.mount("/", StaticFiles(directory=admin_panel_path, html=True), name="admin")
else:
    @app.get("/")
    async def root():
        return {"message": "GORA Hotel Admin API", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
