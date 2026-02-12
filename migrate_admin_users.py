"""
Add phone, role, and permissions columns to admin_users table
"""
from sqlalchemy import create_engine, text
from config import get_settings

def migrate():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Add phone column
        try:
            conn.execute(text("""
                ALTER TABLE admin_users ADD COLUMN phone VARCHAR(32)
            """))
            print("✅ phone column added")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✅ phone column already exists")
            else:
                print(f"⚠️ Error adding phone: {e}")
        
        # Add role column
        try:
            conn.execute(text("""
                ALTER TABLE admin_users ADD COLUMN role VARCHAR(32) DEFAULT 'STAFF' NOT NULL
            """))
            print("✅ role column added")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✅ role column already exists")
            else:
                print(f"⚠️ Error adding role: {e}")
        
        # Add permissions column
        try:
            conn.execute(text("""
                ALTER TABLE admin_users ADD COLUMN permissions TEXT
            """))
            print("✅ permissions column added")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("✅ permissions column already exists")
            else:
                print(f"⚠️ Error adding permissions: {e}")
        
        # Update existing admin users to SUPER_ADMIN role
        try:
            conn.execute(text("""
                UPDATE admin_users SET role = 'SUPER_ADMIN' WHERE role = 'STAFF'
            """))
            print("✅ Existing admin users updated to SUPER_ADMIN role")
        except Exception as e:
            print(f"⚠️ Error updating roles: {e}")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
