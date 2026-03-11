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

    # Migration 2: Add notification_sent column to staff_tasks
    cursor.execute("PRAGMA table_info(staff_tasks)")
    staff_task_columns = [row[1] for row in cursor.fetchall()]

    if "notification_sent" not in staff_task_columns:
        print("Adding notification_sent column to staff_tasks...")
        cursor.execute("ALTER TABLE staff_tasks ADD COLUMN notification_sent BOOLEAN DEFAULT 0 NOT NULL")
        conn.commit()
        print("  Done.")
    else:
        print("notification_sent column already exists, skipping.")

    # Migration 3: Add scheduled_for_utc column to staff_tasks
    cursor.execute("PRAGMA table_info(staff_tasks)")
    staff_task_columns = [row[1] for row in cursor.fetchall()]
    if "scheduled_for_utc" not in staff_task_columns:
        print("Adding scheduled_for_utc column to staff_tasks...")
        cursor.execute("ALTER TABLE staff_tasks ADD COLUMN scheduled_for_utc DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("scheduled_for_utc column already exists, skipping.")

    # Migration 4: Create event_items table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS event_items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            location_text TEXT,
            map_url TEXT,
            image_url TEXT,
            starts_at DATETIME NOT NULL,
            ends_at DATETIME NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT 1
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_items_starts_at ON event_items(starts_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_items_ends_at ON event_items(ends_at)")
    conn.commit()
    print("event_items table ensured.")

    # Migration 5: Create menu_category_settings table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS menu_category_settings (
            id INTEGER PRIMARY KEY,
            category TEXT NOT NULL UNIQUE,
            is_enabled BOOLEAN NOT NULL DEFAULT 0
        )
        """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_menu_category_settings_category ON menu_category_settings(category)")
    cursor.execute("INSERT OR IGNORE INTO menu_category_settings (category, is_enabled) VALUES ('breakfast', 1)")
    cursor.execute("INSERT OR IGNORE INTO menu_category_settings (category, is_enabled) VALUES ('lunch', 0)")
    cursor.execute("INSERT OR IGNORE INTO menu_category_settings (category, is_enabled) VALUES ('dinner', 0)")
    conn.commit()
    print("menu_category_settings table ensured.")

    # Migration 6: Add open-dialog columns to tickets
    cursor.execute("PRAGMA table_info(tickets)")
    ticket_columns = [row[1] for row in cursor.fetchall()]

    if "dialog_open" not in ticket_columns:
        print("Adding dialog_open column to tickets...")
        cursor.execute("ALTER TABLE tickets ADD COLUMN dialog_open BOOLEAN DEFAULT 0 NOT NULL")
        conn.commit()
        print("  Done.")
    else:
        print("dialog_open column already exists, skipping.")

    if "dialog_expires_at" not in ticket_columns:
        print("Adding dialog_expires_at column to tickets...")
        cursor.execute("ALTER TABLE tickets ADD COLUMN dialog_expires_at DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("dialog_expires_at column already exists, skipping.")

    if "dialog_last_activity_at" not in ticket_columns:
        print("Adding dialog_last_activity_at column to tickets...")
        cursor.execute("ALTER TABLE tickets ADD COLUMN dialog_last_activity_at DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("dialog_last_activity_at column already exists, skipping.")

    if "admin_last_viewed_at" not in ticket_columns:
        print("Adding admin_last_viewed_at column to tickets...")
        cursor.execute("ALTER TABLE tickets ADD COLUMN admin_last_viewed_at DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("admin_last_viewed_at column already exists, skipping.")

    # Migration 7: Add event publication window fields
    cursor.execute("PRAGMA table_info(event_items)")
    event_columns = [row[1] for row in cursor.fetchall()]

    if "publish_from" not in event_columns:
        print("Adding publish_from column to event_items...")
        cursor.execute("ALTER TABLE event_items ADD COLUMN publish_from DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("publish_from column already exists, skipping.")

    if "publish_until" not in event_columns:
        print("Adding publish_until column to event_items...")
        cursor.execute("ALTER TABLE event_items ADD COLUMN publish_until DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("publish_until column already exists, skipping.")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_items_publish_from ON event_items(publish_from)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_items_publish_until ON event_items(publish_until)")
    # Backfill legacy rows so visibility window defaults to event dates.
    cursor.execute("UPDATE event_items SET publish_from = starts_at WHERE publish_from IS NULL")
    cursor.execute("UPDATE event_items SET publish_until = ends_at WHERE publish_until IS NULL")
    conn.commit()
    print("event_items publication window ensured.")

    # Migration 8: Add guest notification tracking fields
    cursor.execute("PRAGMA table_info(guest_bookings)")
    guest_booking_columns = [row[1] for row in cursor.fetchall()]

    if "checkin_notified" not in guest_booking_columns:
        print("Adding checkin_notified column to guest_bookings...")
        cursor.execute("ALTER TABLE guest_bookings ADD COLUMN checkin_notified BOOLEAN DEFAULT 0 NOT NULL")
        conn.commit()
        print("  Done.")
    else:
        print("checkin_notified column already exists, skipping.")

    if "checkout_notified" not in guest_booking_columns:
        print("Adding checkout_notified column to guest_bookings...")
        cursor.execute("ALTER TABLE guest_bookings ADD COLUMN checkout_notified BOOLEAN DEFAULT 0 NOT NULL")
        conn.commit()
        print("  Done.")
    else:
        print("checkout_notified column already exists, skipping.")

    # Migration 9: Add phone index for users
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone)")
    conn.commit()
    print("users phone index ensured.")

    # Migration 10: Add Shelter sync fields to guest_bookings
    cursor.execute("PRAGMA table_info(guest_bookings)")
    guest_booking_columns = [row[1] for row in cursor.fetchall()]

    if "shelter_reservation_id" not in guest_booking_columns:
        print("Adding shelter_reservation_id column to guest_bookings...")
        cursor.execute("ALTER TABLE guest_bookings ADD COLUMN shelter_reservation_id TEXT")
        conn.commit()
        print("  Done.")
    else:
        print("shelter_reservation_id column already exists, skipping.")

    if "feedback_requested" not in guest_booking_columns:
        print("Adding feedback_requested column to guest_bookings...")
        cursor.execute("ALTER TABLE guest_bookings ADD COLUMN feedback_requested BOOLEAN DEFAULT 0 NOT NULL")
        conn.commit()
        print("  Done.")
    else:
        print("feedback_requested column already exists, skipping.")

    if "feedback_requested_at" not in guest_booking_columns:
        print("Adding feedback_requested_at column to guest_bookings...")
        cursor.execute("ALTER TABLE guest_bookings ADD COLUMN feedback_requested_at DATETIME")
        conn.commit()
        print("  Done.")
    else:
        print("feedback_requested_at column already exists, skipping.")

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_guest_bookings_shelter_reservation_id ON guest_bookings(shelter_reservation_id)")
    conn.commit()
    print("guest_bookings shelter indexes ensured.")

    # Migration 11: Create shelter_sync_state table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shelter_sync_state (
            id INTEGER PRIMARY KEY,
            last_sync_at DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cursor.execute("INSERT OR IGNORE INTO shelter_sync_state (id, last_sync_at, updated_at) VALUES (1, NULL, CURRENT_TIMESTAMP)")
    conn.commit()
    print("shelter_sync_state table ensured.")
    
    conn.close()
    print("Migrations complete!")


if __name__ == "__main__":
    migrate()
