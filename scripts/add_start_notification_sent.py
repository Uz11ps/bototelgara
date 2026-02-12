import os
import sqlite3

DB_PATH = "gora_bot.db"


def add_column() -> None:
    if not os.path.exists(DB_PATH):
        sqlite3.connect(DB_PATH).close()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staff_tasks'")
        if cursor.fetchone() is None:
            cursor.execute(
                """
                CREATE TABLE staff_tasks (
                    id INTEGER PRIMARY KEY,
                    room_number VARCHAR(32) NOT NULL,
                    task_type VARCHAR(64) NOT NULL,
                    description TEXT,
                    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
                    assigned_to VARCHAR(64),
                    created_at DATETIME,
                    completed_at DATETIME,
                    scheduled_at DATETIME,
                    reminder_sent BOOLEAN NOT NULL DEFAULT 0,
                    start_notification_sent BOOLEAN NOT NULL DEFAULT 0
                )
                """
            )
            conn.commit()

        cursor.execute("PRAGMA table_info(staff_tasks)")
        columns = {info[1] for info in cursor.fetchall()}

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
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    add_column()
