import sqlite3
import os

DB_PATH = "hotel.db"

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(staff_tasks)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "start_notification_sent" not in columns:
            print("Adding start_notification_sent column to staff_tasks...")
            cursor.execute("ALTER TABLE staff_tasks ADD COLUMN start_notification_sent BOOLEAN DEFAULT 0")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column start_notification_sent already exists.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
