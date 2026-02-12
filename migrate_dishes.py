"""
Create menu_item_dishes table migration
"""
from sqlalchemy import create_engine, text
from config import get_settings

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create menu_item_dishes table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS menu_item_dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_item_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                unit VARCHAR(64) NOT NULL,
                FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE CASCADE
            )
        """))
        conn.commit()
        print("✅ menu_item_dishes table created successfully")

if __name__ == "__main__":
    migrate()
