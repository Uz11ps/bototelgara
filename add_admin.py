"""
Add admin user to database.
"""
import os
import sys
from sqlalchemy.orm import Session
from db.session import SessionLocal
from db.models import AdminUser
from datetime import datetime


def add_admin(telegram_id: str, full_name: str = "Administrator"):
    """Add admin user to database."""
    db: Session = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(AdminUser).filter(AdminUser.telegram_id == telegram_id).first()
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.full_name = full_name
                db.commit()
                print(f"Reactivated existing admin: {existing.id}")
            else:
                print(f"Admin already exists and is active: {existing.id}")
            return
        
        # Create new admin
        admin = AdminUser(
            telegram_id=telegram_id,
            full_name=full_name,
            is_active=True,
            created_at=datetime.utcnow()
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created new admin: {admin.id} with telegram_id {admin.telegram_id}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python add_admin.py <telegram_id> [full_name]")
        sys.exit(1)
    
    telegram_id = sys.argv[1]
    full_name = sys.argv[2] if len(sys.argv) > 2 else "Administrator"
    
    add_admin(telegram_id, full_name)
