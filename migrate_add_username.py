"""Migration script to add guest_username column to tickets table."""
import sqlite3
import os
import sys

# Try different possible locations for the database
POSSIBLE_DB_PATHS = [
    "/root/garabotprofi/gora_bot.db",
    "/root/garabotprofi/hotel.db",
    "gora_bot.db",
    "hotel.db",
    "../gora_bot.db",
    "../hotel.db",
    "./gora_bot.db",
    "./hotel.db"
]

def find_db():
    for path in POSSIBLE_DB_PATHS:
        if os.path.exists(path):
            print(f"Found database at: {path}")
            return path
    print("ERROR: Could not find hotel.db")
    print("Searched in:")
    for path in POSSIBLE_DB_PATHS:
        print(f"  - {path}")
    return None

def migrate():
    print("Starting migration...")
    
    db_path = find_db()
    if not db_path:
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column already exists
    try:
        cursor.execute("PRAGMA table_info(tickets)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'guest_username' not in columns:
            print("Adding guest_username column to tickets table...")
            cursor.execute("""
                ALTER TABLE tickets 
                ADD COLUMN guest_username VARCHAR(255)
            """)
            conn.commit()
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Column guest_username already exists, skipping migration.")
    except sqlite3.OperationalError as e:
        print(f"Error during migration: {e}")
        conn.close()
        sys.exit(1)
    
    conn.close()
    print("Done!")

if __name__ == "__main__":
    migrate()
