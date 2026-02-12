import sqlite3
import os

DB_PATH = "hotel.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Add scheduled_at column
        try:
            cursor.execute("ALTER TABLE staff_tasks ADD COLUMN scheduled_at DATETIME")
            print("Added column: scheduled_at")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print("Column scheduled_at already exists")
            else:
                raise e

        # Add reminder_sent column
        try:
            cursor.execute("ALTER TABLE staff_tasks ADD COLUMN reminder_sent BOOLEAN DEFAULT 0")
            print("Added column: reminder_sent")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print("Column reminder_sent already exists")
            else:
                raise e

        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
