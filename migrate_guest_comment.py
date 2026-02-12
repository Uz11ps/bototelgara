"""
Add guest_comment column to menu_items table
"""
from sqlalchemy import create_engine, text
from config import get_settings

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Add guest_comment column to menu_items
        try:
            conn.execute(text("""
                ALTER TABLE menu_items ADD COLUMN guest_comment TEXT
            """))
            conn.commit()
            print("✅ guest_comment column added successfully")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✅ guest_comment column already exists")
            else:
                raise e

if __name__ == "__main__":
    migrate()
