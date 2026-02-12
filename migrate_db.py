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
    
    # Migration 2: Add new columns to staff_tasks
    cursor.execute("PRAGMA table_info(staff_tasks)")
    staff_task_columns = [row[1] for row in cursor.fetchall()]
    
    new_columns = [
        ("assigned_to_id", "INTEGER"),
        ("delivery_time", "VARCHAR(16)"),
        ("quantity", "INTEGER"),
        ("ticket_id", "INTEGER"),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in staff_task_columns:
            print(f"Adding {col_name} column to staff_tasks...")
            cursor.execute(f"ALTER TABLE staff_tasks ADD COLUMN {col_name} {col_type}")
            conn.commit()
            print(f"  Done.")
        else:
            print(f"{col_name} column already exists, skipping.")
    
    # Migration 3: Add telegram_id column to tickets if missing
    cursor.execute("PRAGMA table_info(tickets)")
    ticket_columns = [row[1] for row in cursor.fetchall()]
    
    if "telegram_id" not in ticket_columns:
        print("Adding telegram_id column to tickets...")
        cursor.execute("ALTER TABLE tickets ADD COLUMN telegram_id VARCHAR(64)")
        conn.commit()
        print("  Done.")
    else:
        print("telegram_id column already exists, skipping.")
    
    conn.close()
    print("Migrations complete!")


if __name__ == "__main__":
    migrate()
