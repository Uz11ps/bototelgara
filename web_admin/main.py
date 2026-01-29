"""
FastAPI web admin panel for managing hotel tickets.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.models import Ticket, TicketMessage, TicketMessageSender, TicketStatus, TicketType
from db.session import SessionLocal


logger = logging.getLogger(__name__)
app = FastAPI(title="GORA Hotel Admin API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
@app.get("/")
async def root():
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
