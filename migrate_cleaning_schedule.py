"""
Database migration script to add guest_stays and cleaning_schedules tables
"""
from sqlalchemy import create_engine, text
from config import get_settings


def migrate():
    """Create guest_stays and cleaning_schedules tables"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    print("Running migration: Adding guest_stays and cleaning_schedules tables...")
    
    with engine.connect() as conn:
        # Create guest_stays table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS guest_stays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id VARCHAR(64),
                    telegram_username VARCHAR(255),
                    guest_name VARCHAR(255),
                    room_number VARCHAR(32) NOT NULL,
                    check_in_date DATE NOT NULL,
                    check_out_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    auto_cleaning_enabled BOOLEAN DEFAULT 1 NOT NULL,
                    checkin_code VARCHAR(32) UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("✅ Created guest_stays table")
            
            # Create indexes for guest_stays
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_telegram_id ON guest_stays(telegram_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_telegram_username ON guest_stays(telegram_username)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_room_number ON guest_stays(room_number)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_checkin_code ON guest_stays(checkin_code)"))
            print("✅ Created indexes for guest_stays")
            
        except Exception as e:
            print(f"⚠️  guest_stays table might already exist: {e}")
        
        # Create cleaning_schedules table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cleaning_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guest_stay_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    time_slot VARCHAR(32),
                    notification_sent BOOLEAN DEFAULT 0 NOT NULL,
                    notification_sent_at TIMESTAMP,
                    response_received BOOLEAN DEFAULT 0 NOT NULL,
                    response_received_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (guest_stay_id) REFERENCES guest_stays(id)
                )
            """))
            print("✅ Created cleaning_schedules table")
            
            # Create indexes for cleaning_schedules
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cleaning_schedules_guest_stay_id ON cleaning_schedules(guest_stay_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cleaning_schedules_date ON cleaning_schedules(date)"))
            print("✅ Created indexes for cleaning_schedules")
            
        except Exception as e:
            print(f"⚠️  cleaning_schedules table might already exist: {e}")
        
        conn.commit()
    
    print("✅ Migration completed successfully!")


if __name__ == "__main__":
    migrate()
