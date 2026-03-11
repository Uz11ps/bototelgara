"""
FastAPI web admin panel for managing hotel tickets.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import subprocess
import asyncio
import yaml
from uuid import uuid4
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_

from db.models import (
    Ticket,
    TicketMessage,
    TicketMessageSender,
    TicketStatus,
    TicketType,
    MenuItem,
    GuideItem,
    EventItem,
    StaffTask,
    User,
    Staff,
    StaffRole,
    GuestBooking,
    CleaningRequest,
    MenuCategory,
    MenuCategorySetting,
    AdminUser,
)
from db.session import SessionLocal
from services.shelter import get_shelter_client, ShelterAPIError
from services.content import content_manager


logger = logging.getLogger(__name__)
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
    dialog_open: bool = False
    dialog_expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    has_new_guest_message: bool = False
    new_guest_messages_count: int = 0
    
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


class ContentUpdateRequest(BaseModel):
    content: str


class ButtonLabelUpdateItem(BaseModel):
    path: str
    label: str


class ButtonLabelsUpdateRequest(BaseModel):
    updates: List[ButtonLabelUpdateItem]


class CategoryAvailabilityRequest(BaseModel):
    is_enabled: bool


def _menus_file_path() -> str:
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, "content", "menus.ru.yml")


def _texts_file_path() -> str:
    project_root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(project_root, "content", "texts.ru.yml")


def _collect_button_labels(node: Any, prefix: str = "") -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if isinstance(node, list):
        for idx, item in enumerate(node):
            current_prefix = f"{prefix}[{idx}]"
            if isinstance(item, dict) and isinstance(item.get("label"), str):
                items.append(
                    {
                        "path": f"{current_prefix}.label",
                        "label": item["label"],
                        "callback_data": item.get("callback_data"),
                        "web_app": item.get("web_app"),
                    }
                )
            items.extend(_collect_button_labels(item, current_prefix))
    elif isinstance(node, dict):
        for key, value in node.items():
            current_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(_collect_button_labels(value, current_prefix))
    return items


def _path_tokens(path: str) -> list[str | int]:
    tokens: list[str | int] = []
    key = ""
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if key:
                tokens.append(key)
                key = ""
            i += 1
            continue
        if ch == "[":
            if key:
                tokens.append(key)
                key = ""
            j = path.find("]", i)
            if j == -1:
                raise ValueError(f"Invalid path: {path}")
            tokens.append(int(path[i + 1:j]))
            i = j + 1
            continue
        key += ch
        i += 1
    if key:
        tokens.append(key)
    return tokens


def _set_value_by_path(root: Any, path: str, value: Any) -> None:
    tokens = _path_tokens(path)
    if not tokens:
        raise ValueError(f"Invalid path: {path}")
    cur = root
    for token in tokens[:-1]:
        if isinstance(token, int):
            if not isinstance(cur, list):
                raise ValueError(f"Expected list at token {token} for path {path}")
            cur = cur[token]
        else:
            if not isinstance(cur, dict):
                raise ValueError(f"Expected dict at token {token} for path {path}")
            cur = cur[token]
    last = tokens[-1]
    if isinstance(last, int):
        if not isinstance(cur, list):
            raise ValueError(f"Expected list for final token in path {path}")
        cur[last] = value
    else:
        if not isinstance(cur, dict):
            raise ValueError(f"Expected dict for final token in path {path}")
        cur[last] = value


def _sorted_ticket_messages(ticket: Ticket) -> list[TicketMessage]:
    return sorted(ticket.messages or [], key=lambda message: message.created_at)


def _new_guest_messages_count(ticket: Ticket) -> int:
    """Количество непрочитанных сообщений гостя (показываем значок 🔔 только при наличии)."""
    if ticket.status not in {TicketStatus.NEW, TicketStatus.PENDING_ADMIN}:
        return 0

    messages = _sorted_ticket_messages(ticket)
    # Берём максимальную из: последний ответ админа или момент просмотра заявки админом
    last_admin_at = max(
        (message.created_at for message in messages if message.sender == TicketMessageSender.ADMIN),
        default=None,
    )
    read_threshold = last_admin_at
    if getattr(ticket, "admin_last_viewed_at", None) is not None:
        read_threshold = max(read_threshold or datetime.min, ticket.admin_last_viewed_at)

    count = 0
    for message in messages:
        if message.sender != TicketMessageSender.GUEST:
            continue
        if read_threshold is None or message.created_at > read_threshold:
            count += 1
    return count


def _last_message_at(ticket: Ticket) -> datetime:
    messages = _sorted_ticket_messages(ticket)
    if messages:
        return messages[-1].created_at
    return ticket.updated_at


def _serialize_message(message: TicketMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        sender=message.sender.value if hasattr(message.sender, "value") else str(message.sender),
        content=message.content,
        created_at=message.created_at,
        admin_telegram_id=message.admin_telegram_id,
        admin_name=message.admin_name,
    )


def _serialize_ticket(ticket: Ticket) -> TicketResponse:
    new_count = _new_guest_messages_count(ticket)
    return TicketResponse(
        id=ticket.id,
        type=ticket.type.value if hasattr(ticket.type, "value") else str(ticket.type),
        status=ticket.status.value if hasattr(ticket.status, "value") else str(ticket.status),
        guest_chat_id=ticket.guest_chat_id,
        guest_name=ticket.guest_name,
        room_number=ticket.room_number,
        dialog_open=bool(ticket.dialog_open),
        dialog_expires_at=ticket.dialog_expires_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        last_message_at=_last_message_at(ticket),
        has_new_guest_message=new_count > 0,
        new_guest_messages_count=new_count,
    )


def _serialize_ticket_detail(ticket: Ticket) -> TicketDetailResponse:
    base = _serialize_ticket(ticket)
    return TicketDetailResponse(
        **base.model_dump(),
        messages=[_serialize_message(message) for message in _sorted_ticket_messages(ticket)],
        payload=ticket.payload,
    )


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
    query = db.query(Ticket).options(selectinload(Ticket.messages))
    
    if status:
        try:
            status_enum = TicketStatus(status)
            query = query.filter(Ticket.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    tickets = query.order_by(Ticket.updated_at.desc()).all()
    return [_serialize_ticket(ticket) for ticket in tickets]


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket_detail(ticket_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific ticket. При открытии заявки — помечаем прочитанной."""
    ticket = (
        db.query(Ticket)
        .options(selectinload(Ticket.messages))
        .filter(Ticket.id == ticket_id)
        .first()
    )
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Админ открыл заявку — сбрасываем значок непрочитанных
    ticket.admin_last_viewed_at = datetime.utcnow()
    db.commit()
    
    return _serialize_ticket_detail(ticket)


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
    ticket.updated_at = datetime.utcnow()
    if ticket.dialog_open:
        ticket.dialog_last_activity_at = datetime.utcnow()
        ticket.dialog_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    db.refresh(message)
    
    return message


@app.post("/api/tickets/{ticket_id}/dialog/close")
async def close_ticket_dialog(ticket_id: int, db: Session = Depends(get_db)):
    """Manually close an open guest-admin dialog."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    ticket.dialog_open = False
    ticket.dialog_expires_at = None
    ticket.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True, "ticket_id": ticket_id, "dialog_open": False}


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
    
    previous_status = ticket.status
    ticket.status = new_status
    if new_status in {TicketStatus.COMPLETED, TicketStatus.DECLINED, TicketStatus.CANCELLED}:
        ticket.dialog_open = False
        ticket.dialog_expires_at = None
    ticket.updated_at = datetime.utcnow()
    
    # Queue a system notification for Telegram delivery when the status changes.
    try:
        notification_text = None
        if new_status == TicketStatus.COMPLETED:
            notification_text = content_manager.get_text("tickets.resolved").format(ticket_id=ticket_id)
        elif new_status == TicketStatus.DECLINED:
            notification_text = content_manager.get_text("tickets.declined").format(ticket_id=ticket_id)

        if (
            notification_text
            and previous_status != new_status
            and bool((ticket.guest_chat_id or "").strip())
        ):
            db.add(
                TicketMessage(
                    ticket_id=ticket.id,
                    sender=TicketMessageSender.SYSTEM,
                    content=notification_text,
                    request_id=str(uuid4()),
                )
            )
    except Exception as e:
        logger.error(f"Failed to queue ticket status notification: {e}")
    
    db.commit()
    
    return {"message": f"Ticket #{ticket_id} status updated to {new_status.value}"}

@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Delete a ticket completely."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Also delete associated messages
    db.query(TicketMessage).filter(TicketMessage.ticket_id == ticket_id).delete()
    
    db.delete(ticket)
    db.commit()
    return {"message": f"Ticket #{ticket_id} deleted"}

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

@app.get("/api/content/menus-ru")
async def get_menus_ru_content():
    """Get raw content of menus.ru.yml for admin editing."""
    menus_path = _menus_file_path()
    if not os.path.exists(menus_path):
        raise HTTPException(status_code=404, detail="menus.ru.yml not found")
    with open(menus_path, "r", encoding="utf-8") as f:
        return {"content": f.read()}


@app.put("/api/content/menus-ru")
async def update_menus_ru_content(payload: ContentUpdateRequest):
    """Update menus.ru.yml after YAML validation."""
    try:
        parsed = yaml.safe_load(payload.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML error: {e}")

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Root YAML node must be a mapping/object")

    menus_path = _menus_file_path()
    with open(menus_path, "w", encoding="utf-8") as f:
        f.write(payload.content)
    content_manager.reload()

    return {"success": True}


class TextUpdateByPathRequest(BaseModel):
    path: str
    value: str


@app.get("/api/content/texts-ru/json")
async def get_texts_ru_json():
    """Get parsed content of texts.ru.yml as JSON."""
    texts_path = _texts_file_path()
    if not os.path.exists(texts_path):
        raise HTTPException(status_code=404, detail="texts.ru.yml not found")
    with open(texts_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise HTTPException(status_code=500, detail=f"YAML parse error: {e}")


@app.put("/api/content/texts-ru/json")
async def update_texts_ru_json(payload: TextUpdateByPathRequest):
    """Update a specific text value in texts.ru.yml by path."""
    texts_path = _texts_file_path()
    if not os.path.exists(texts_path):
        raise HTTPException(status_code=404, detail="texts.ru.yml not found")

    with open(texts_path, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f) or {}

    try:
        _set_value_by_path(parsed, payload.path, payload.value)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid path {payload.path}: {e}")

    with open(texts_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(parsed, f, allow_unicode=True, sort_keys=False)
    content_manager.reload()

    return {"success": True}


@app.get("/api/content/menus-ru/json")
async def get_menus_ru_json():
    """Get parsed content of menus.ru.yml as JSON."""
    menus_path = _menus_file_path()
    if not os.path.exists(menus_path):
        raise HTTPException(status_code=404, detail="menus.ru.yml not found")
    with open(menus_path, "r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise HTTPException(status_code=500, detail=f"YAML parse error: {e}")


@app.get("/api/content/texts-ru")
async def get_texts_ru_content():
    """Get raw content of texts.ru.yml for admin editing."""
    texts_path = _texts_file_path()
    if not os.path.exists(texts_path):
        raise HTTPException(status_code=404, detail="texts.ru.yml not found")
    with open(texts_path, "r", encoding="utf-8") as f:
        return {"content": f.read()}


@app.put("/api/content/texts-ru")
async def update_texts_ru_content(payload: ContentUpdateRequest):
    """Update texts.ru.yml after YAML validation."""
    try:
        parsed = yaml.safe_load(payload.content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"YAML error: {e}")

    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Root YAML node must be a mapping/object")

    texts_path = _texts_file_path()
    with open(texts_path, "w", encoding="utf-8") as f:
        f.write(payload.content)
    content_manager.reload()

    return {"success": True}


@app.get("/api/content/button-labels")
async def get_button_labels():
    """Get all editable button labels from menus.ru.yml."""
    menus_path = _menus_file_path()
    if not os.path.exists(menus_path):
        raise HTTPException(status_code=404, detail="menus.ru.yml not found")
    with open(menus_path, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f) or {}
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Invalid menus.ru.yml structure")
    buttons = _collect_button_labels(parsed)
    buttons.sort(key=lambda x: x["path"])
    return {"buttons": buttons}


@app.put("/api/content/button-labels")
async def update_button_labels(payload: ButtonLabelsUpdateRequest):
    """Update only labels of buttons while preserving callback/web_app values."""
    menus_path = _menus_file_path()
    if not os.path.exists(menus_path):
        raise HTTPException(status_code=404, detail="menus.ru.yml not found")

    with open(menus_path, "r", encoding="utf-8") as f:
        parsed = yaml.safe_load(f) or {}
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Invalid menus.ru.yml structure")

    for item in payload.updates:
        label = (item.label or "").strip()
        if not label:
            raise HTTPException(status_code=400, detail=f"Label cannot be empty: {item.path}")
        try:
            _set_value_by_path(parsed, item.path, label)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid path {item.path}: {e}")

    with open(menus_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(parsed, f, allow_unicode=True, sort_keys=False)
    content_manager.reload()

    return {"success": True, "updated": len(payload.updates)}

@app.get("/api/menu")
async def get_menu(db: Session = Depends(get_db)):
    return db.query(MenuItem).all()


def _ensure_menu_category_settings(db: Session) -> dict[str, bool]:
    defaults = {
        MenuCategory.BREAKFAST.value: True,
        MenuCategory.LUNCH.value: False,
        MenuCategory.DINNER.value: False,
    }
    legacy_map = {
        "BREAKFAST": MenuCategory.BREAKFAST.value,
        "LUNCH": MenuCategory.LUNCH.value,
        "DINNER": MenuCategory.DINNER.value,
    }

    # Normalize legacy enum-name rows (BREAKFAST/LUNCH/DINNER) into lowercase values.
    legacy_rows = db.query(MenuCategorySetting).filter(
        MenuCategorySetting.category.in_(list(legacy_map.keys()))
    ).all()
    for legacy in legacy_rows:
        target = legacy_map.get(str(legacy.category))
        if not target:
            continue
        target_row = db.query(MenuCategorySetting).filter(MenuCategorySetting.category == target).first()
        if target_row is None:
            db.add(MenuCategorySetting(category=target, is_enabled=bool(legacy.is_enabled)))
        else:
            # Preserve "enabled" if it was switched on in any legacy row.
            if bool(legacy.is_enabled) and not bool(target_row.is_enabled):
                target_row.is_enabled = True
        db.delete(legacy)

    changed = False
    for cat, default_enabled in defaults.items():
        row = db.query(MenuCategorySetting).filter(MenuCategorySetting.category == cat).first()
        if row is None:
            db.add(MenuCategorySetting(category=cat, is_enabled=default_enabled))
            changed = True
    if changed or legacy_rows:
        db.commit()

    settings = db.query(MenuCategorySetting).all()
    normalized: dict[str, bool] = {}
    for s in settings:
        key = str(s.category).lower()
        normalized[key] = bool(s.is_enabled)
    return normalized


@app.get("/api/menu/category-settings")
async def get_menu_category_settings(db: Session = Depends(get_db)):
    return _ensure_menu_category_settings(db)


@app.patch("/api/menu/category/{category}/enabled")
async def set_menu_category_enabled(category: str, payload: CategoryAvailabilityRequest, db: Session = Depends(get_db)):
    try:
        cat_enum = MenuCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid menu category")

    _ensure_menu_category_settings(db)
    row = db.query(MenuCategorySetting).filter(MenuCategorySetting.category == cat_enum.value).first()
    if row is None:
        row = MenuCategorySetting(category=cat_enum.value, is_enabled=payload.is_enabled)
        db.add(row)
    else:
        row.is_enabled = payload.is_enabled
    db.commit()
    return {"category": cat_enum.value, "is_enabled": bool(payload.is_enabled)}

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


@app.get("/api/events")
async def get_events(db: Session = Depends(get_db)):
    return db.query(EventItem).order_by(EventItem.starts_at.asc()).all()


@app.get("/api/events/active")
async def get_active_events(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return db.query(EventItem).filter(
        EventItem.is_active == True,
        or_(EventItem.publish_from.is_(None), EventItem.publish_from <= now),
        or_(EventItem.publish_until.is_(None), EventItem.publish_until >= now),
    ).order_by(EventItem.starts_at.asc()).all()


def _normalize_event_payload(payload: dict) -> dict:
    normalized = dict(payload or {})
    for key in ("starts_at", "ends_at", "publish_from", "publish_until"):
        value = normalized.get(key)
        if value == "":
            normalized[key] = None
            continue
        if isinstance(value, str):
            try:
                normalized[key] = datetime.fromisoformat(value)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid datetime for {key}")
    starts_at = normalized.get("starts_at")
    ends_at = normalized.get("ends_at")
    if not starts_at or not ends_at:
        raise HTTPException(status_code=400, detail="starts_at and ends_at are required")
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="ends_at must be later than starts_at")

    if normalized.get("publish_from") is None:
        # By default, announcement becomes visible immediately.
        normalized["publish_from"] = datetime.utcnow()
    if normalized.get("publish_until") is None:
        normalized["publish_until"] = ends_at

    publish_from = normalized.get("publish_from")
    publish_until = normalized.get("publish_until")
    if publish_from and publish_until and publish_until < publish_from:
        raise HTTPException(status_code=400, detail="publish_until must be later than publish_from")
    return normalized


@app.post("/api/events")
async def create_event_item(item: dict, db: Session = Depends(get_db)):
    new_item = EventItem(**_normalize_event_payload(item))
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.post("/api/events/upload-image")
async def upload_event_image(file: UploadFile = File(...)):
    """Upload image file for event and return public URL."""
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    uploads_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_panel", "uploads", "events")
    os.makedirs(uploads_root, exist_ok=True)

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    filename = f"{uuid4().hex}{ext}"
    file_path = os.path.join(uploads_root, filename)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Empty file")
    with open(file_path, "wb") as f:
        f.write(contents)

    return {"url": f"/uploads/events/{filename}"}


@app.put("/api/events/{item_id}")
async def update_event_item(item_id: int, item_data: dict, db: Session = Depends(get_db)):
    item = db.query(EventItem).filter(EventItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Event item not found")
    normalized = _normalize_event_payload({**{
        "name": item.name,
        "description": item.description,
        "location_text": item.location_text,
        "map_url": item.map_url,
        "image_url": item.image_url,
        "starts_at": item.starts_at,
        "ends_at": item.ends_at,
        "publish_from": item.publish_from,
        "publish_until": item.publish_until,
        "is_active": item.is_active,
    }, **item_data})
    for key, value in normalized.items():
        if hasattr(item, key):
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/api/events/{item_id}")
async def delete_event_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(EventItem).filter(EventItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Event item not found")
    db.delete(item)
    db.commit()
    return {"message": f"Event item {item_id} deleted"}

@app.get("/api/staff/tasks")
async def get_staff_tasks(db: Session = Depends(get_db)):
    return db.query(StaffTask).order_by(StaffTask.created_at.desc()).all()

@app.post("/api/staff/tasks")
async def create_staff_task(task: dict, db: Session = Depends(get_db)):
    # Notification timing (MSK): "now" or explicit HH:MM.
    notify_mode = (task.pop("notify_mode", "now") or "now").strip().lower()
    notify_time_msk = (task.pop("notify_time_msk", "") or "").strip()
    scheduled_for_utc = None
    if notify_mode == "at_time" and notify_time_msk:
        try:
            # MSK is UTC+3 all year.
            hh, mm = [int(x) for x in notify_time_msk.split(":")]
            now_utc = datetime.utcnow()
            now_msk = now_utc + timedelta(hours=3)
            target_msk = now_msk.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target_msk <= now_msk:
                target_msk = target_msk + timedelta(days=1)
            scheduled_for_utc = target_msk - timedelta(hours=3)
        except Exception:
            raise HTTPException(status_code=400, detail="Неверный формат времени. Используйте HH:MM")

    assigned_to = task.get("assigned_to")
    notification_sent = False

    # Preferred assignment format is staff id from admin panel.
    if assigned_to:
        staff = None
        assigned_str = str(assigned_to)
        if assigned_str.isdigit():
            staff = db.query(Staff).filter(Staff.id == int(assigned_str), Staff.is_active == True).first()
        else:
            # Backward compatibility for legacy tasks assigned by telegram_id.
            staff = db.query(Staff).filter(Staff.telegram_id == assigned_str, Staff.is_active == True).first()

        if not staff:
            raise HTTPException(status_code=400, detail="Assigned staff member not found or inactive")

        # Persist staff id for stable mapping even if telegram id changes later.
        task["assigned_to"] = str(staff.id)
        # If staff has no Telegram ID, don't keep retrying notifications forever.
        notification_sent = not bool(staff.telegram_id)
    else:
        notification_sent = True

    task["notification_sent"] = task.get("notification_sent", notification_sent)
    task["scheduled_for_utc"] = scheduled_for_utc
    new_task = StaffTask(**task)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task

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
    """Delete a completed staff task."""
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Staff task not found")
    if task.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Можно удалять только выполненные задачи")

    db.delete(task)
    db.commit()
    return {"success": True}


@app.get("/api/pending-staff-task-notifications")
async def get_pending_staff_task_notifications(db: Session = Depends(get_db)):
    """Get staff tasks that need Telegram notification to assigned staff."""
    now_utc = datetime.utcnow()
    pending = db.query(StaffTask).filter(
        StaffTask.notification_sent == False,
        StaffTask.status == "PENDING",
        StaffTask.assigned_to.isnot(None),
        or_(StaffTask.scheduled_for_utc.is_(None), StaffTask.scheduled_for_utc <= now_utc),
    ).order_by(StaffTask.created_at.asc()).all()

    notifications = []
    for task in pending:
        staff = None
        assigned_raw = (task.assigned_to or "").strip()

        if assigned_raw.isdigit():
            staff = db.query(Staff).filter(Staff.id == int(assigned_raw), Staff.is_active == True).first()
        elif assigned_raw:
            staff = db.query(Staff).filter(Staff.telegram_id == assigned_raw, Staff.is_active == True).first()

        if not staff:
            # No valid assignee left -> mark as processed to avoid endless polling.
            task.notification_sent = True
            continue

        if not staff.telegram_id or not staff.telegram_id.isdigit():
            task.notification_sent = True
            continue

        notifications.append(
            {
                "task_id": task.id,
                "telegram_id": staff.telegram_id,
                "staff_name": staff.full_name,
                "room_number": task.room_number,
                "task_type": task.task_type,
                "description": task.description or "",
            }
        )

    db.commit()
    return notifications


@app.post("/api/staff/tasks/{task_id}/mark-notified")
async def mark_staff_task_notified(task_id: int, db: Session = Depends(get_db)):
    task = db.query(StaffTask).filter(StaffTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Staff task not found")
    task.notification_sent = True
    db.commit()
    return {"success": True}

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


@app.post("/api/admin-users")
async def create_admin_user(telegram_id: str, full_name: Optional[str] = None, db: Session = Depends(get_db)):
    """Add a new admin user."""
    # Check if already exists
    existing = db.query(AdminUser).filter(AdminUser.telegram_id == telegram_id).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.full_name = full_name
            db.commit()
            return existing
        else:
            raise HTTPException(status_code=400, detail="Admin user already exists and is active")
    
    # Create new admin
    from uuid import uuid4
    admin = AdminUser(
        telegram_id=telegram_id,
        full_name=full_name,
        is_active=True,
        created_at=datetime.utcnow()
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


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
    
    # Add initial message
    message = TicketMessage(
        ticket_id=ticket.id,
        request_id=str(uuid4()),
        sender=TicketMessageSender.GUEST,
        content=summary,
    )
    db.add(message)
    db.commit()
    
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
    # Find ALL unnotified MENU_ORDER tickets with telegram_id (no time window!)
    tickets = db.query(Ticket).filter(
        Ticket.type == TicketType.MENU_ORDER,
        Ticket.guest_chat_id != "mini_app",  # Has telegram_id
    ).all()
    
    notifications = []
    for ticket in tickets:
        # Check if notification was already sent (tracked in payload)
        payload = ticket.payload or {}
        if payload.get("guest_notified"):
            continue
        
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
    
    return notifications


@app.post("/api/mark-notification-sent/{ticket_id}")
async def mark_notification_sent(ticket_id: int, db: Session = Depends(get_db)):
    """Mark order notification as sent to guest."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Update payload to mark as notified - reassign entire dict for SQLAlchemy change detection
    payload = dict(ticket.payload or {})
    payload["guest_notified"] = True
    ticket.payload = payload
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(ticket, "payload")
    db.commit()
    
    return {"success": True}


# --- Undelivered Admin Messages ---

@app.get("/api/undelivered-admin-messages")
async def get_undelivered_admin_messages(db: Session = Depends(get_db)):
    """Get outbound ticket messages that haven't been delivered to users via bot."""
    messages = db.query(TicketMessage).filter(
        TicketMessage.sender.in_([TicketMessageSender.ADMIN, TicketMessageSender.SYSTEM]),
        TicketMessage.bot_delivered == False,
    ).all()
    
    result = []
    for msg in messages:
        ticket = db.query(Ticket).filter(Ticket.id == msg.ticket_id).first()
        if not ticket or not ticket.guest_chat_id:
            continue
        
        result.append({
            "message_id": msg.id,
            "ticket_id": ticket.id,
            "guest_chat_id": ticket.guest_chat_id,
            "content": msg.content,
            "admin_name": msg.admin_name or "Администратор",
            "sender": msg.sender.value if hasattr(msg.sender, "value") else str(msg.sender),
        })
    
    return result


@app.post("/api/mark-message-delivered/{message_id}")
async def mark_message_delivered(message_id: int, db: Session = Depends(get_db)):
    """Mark an admin message as delivered to user via bot."""
    msg = db.query(TicketMessage).filter(TicketMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    msg.bot_delivered = True
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
uploads_path = os.path.join(admin_panel_path, "uploads")

if os.path.exists(admin_panel_path):
    @app.get("/admin")
    async def serve_admin():
        return FileResponse(
            os.path.join(admin_panel_path, "index.html"),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

if os.path.exists(uploads_path):
    app.mount("/uploads", StaticFiles(directory=uploads_path), name="uploads")

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
