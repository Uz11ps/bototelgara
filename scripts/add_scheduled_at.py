import os
import sqlite3


DB_PATH = "gora_bot.db"


def ensure_table_exists(cursor: sqlite3.Cursor) -> bool:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='staff_tasks'")
    return cursor.fetchone() is not None


def add_column_if_missing(cursor: sqlite3.Cursor, column_name: str, column_sql: str) -> None:
    cursor.execute("PRAGMA table_info(staff_tasks)")
    columns = {info[1] for info in cursor.fetchall()}
    if column_name in columns:
        print(f"Column {column_name} already exists")
        return

    cursor.execute(f"ALTER TABLE staff_tasks ADD COLUMN {column_sql}")
    print(f"Added column: {column_name}")


def migrate() -> None:
    if not os.path.exists(DB_PATH):
        sqlite3.connect(DB_PATH).close()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if not ensure_table_exists(cursor):
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

        add_column_if_missing(cursor, "scheduled_at", "scheduled_at DATETIME")
        add_column_if_missing(cursor, "reminder_sent", "reminder_sent BOOLEAN DEFAULT 0")
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
