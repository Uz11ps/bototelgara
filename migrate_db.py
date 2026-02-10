"""
Database migration script.
Safely adds new columns without dropping existing data.
"""
import sqlite3
import os


def get_db_path():
    """Get the database path from environment or default."""
    db_url = os.environ.get("DATABASE_URL", "sqlite:///gora_bot.db")
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    return "gora_bot.db"


def migrate():
    db_path = get_db_path()
    print(f"Running migrations on: {db_path}")
    
    if not os.path.exists(db_path):
        print("Database file not found, skipping migrations (will be created on first run)")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Migration 1: Add bot_delivered column to ticket_messages
    cursor.execute("PRAGMA table_info(ticket_messages)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "bot_delivered" not in columns:
        print("Adding bot_delivered column to ticket_messages...")
        cursor.execute("ALTER TABLE ticket_messages ADD COLUMN bot_delivered BOOLEAN DEFAULT 0 NOT NULL")
        # Mark all existing admin messages as already delivered (don't re-deliver old messages)
        cursor.execute("UPDATE ticket_messages SET bot_delivered = 1 WHERE sender = 'ADMIN'")
        conn.commit()
        print(f"  Done. Marked existing admin messages as delivered.")
    else:
        print("bot_delivered column already exists, skipping.")
    
    conn.close()
    print("Migrations complete!")


if __name__ == "__main__":
    migrate()
