"""
Create admin user in database
"""
import sqlite3
from passlib.context import CryptContext
import uuid

# Password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Connect to database
conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

try:
    # Check if users table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print("❌ Users table doesn't exist! Please start the server first to create tables.")
        exit(1)
    
    # Create admin user
    admin_id = str(uuid.uuid4())
    email = "admin@altayar.com"
    username = "admin"
    password = "Admin123"  # Change this!
    hashed_password = pwd_context.hash(password)
    
    print("🔐 Creating admin user...")
    print("─" * 60)
    
    cursor.execute("""
        INSERT INTO users (
            id, email, username, hashed_password, 
            full_name, phone, role, is_active, is_verified
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        admin_id,
        email,
        username,
        hashed_password,
        "System Admin",
        "+1234567890",
        "ADMIN",
        1,
        1
    ))
    
    conn.commit()
    
    print("✅ Admin user created successfully!")
    print("─" * 60)
    print(f"📧 Email:    {email}")
    print(f"👤 Username: {username}")
    print(f"🔑 Password: {password}")
    print("─" * 60)
    print("\n⚠️  IMPORTANT: Change the password after first login!")
    
except sqlite3.IntegrityError:
    print("⚠️  Admin user already exists!")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
