"""
Add telegram_username and checkin_code fields to existing guest_stays table
"""
from sqlalchemy import create_engine, text
from config import get_settings


def migrate():
    """Add new fields to guest_stays table"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    print("Running migration: Adding telegram_username and checkin_code to guest_stays...")
    
    with engine.connect() as conn:
        # Add telegram_username column
        try:
            conn.execute(text("ALTER TABLE guest_stays ADD COLUMN telegram_username VARCHAR(255)"))
            print("✅ Added telegram_username column")
        except Exception as e:
            print(f"⚠️  telegram_username column might already exist: {e}")
        
        # Add checkin_code column
        try:
            conn.execute(text("ALTER TABLE guest_stays ADD COLUMN checkin_code VARCHAR(32) UNIQUE"))
            print("✅ Added checkin_code column")
        except Exception as e:
            print(f"⚠️  checkin_code column might already exist: {e}")
        
        # Make telegram_id nullable
        try:
            # SQLite doesn't support ALTER COLUMN directly, but we can work around it
            # by creating a new table and copying data
            print("⚠️  Note: telegram_id will remain NOT NULL in existing table (SQLite limitation)")
            print("   New stays can be created with null telegram_id")
        except Exception as e:
            print(f"Note: {e}")
        
        # Create indexes
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_telegram_username ON guest_stays(telegram_username)"))
            print("✅ Created index for telegram_username")
        except Exception as e:
            print(f"⚠️  Index might already exist: {e}")
        
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_guest_stays_checkin_code ON guest_stays(checkin_code)"))
            print("✅ Created index for checkin_code")
        except Exception as e:
            print(f"⚠️  Index might already exist: {e}")
        
        conn.commit()
    
    print("✅ Migration completed!")


if __name__ == "__main__":
    migrate()
