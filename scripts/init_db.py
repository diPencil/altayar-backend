"""
Initialize database with all essential tables and admin user
"""
import sqlite3
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_PATH = 'altayar.db'

print("🚀 Initializing Altayar Database...")
print("=" * 70)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 1. Create users table
    print("\n📋 Creating users table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            phone TEXT,
            avatar TEXT,
            gender TEXT,
            country TEXT,
            birthdate DATETIME,
            membership_id_display TEXT,
            role TEXT DEFAULT 'CUSTOMER',
            employee_type TEXT,
            status TEXT DEFAULT 'ACTIVE',
            language TEXT DEFAULT 'ar',
            email_verified BOOLEAN DEFAULT 0,
            email_verified_at DATETIME,
            phone_verified BOOLEAN DEFAULT 0,
            phone_verified_at DATETIME,
            last_login_at DATETIME,
            login_count INTEGER DEFAULT 0,
            assigned_employee_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME
        )
    """)
    print("✓ Users table created")
    
    # 2. Create membership_plans table
    print("\n📋 Creating membership_plans table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS membership_plans (
            id TEXT PRIMARY KEY,
            tier_code TEXT UNIQUE NOT NULL,
            tier_name_ar TEXT NOT NULL,
            tier_name_en TEXT NOT NULL,
            tier_order INTEGER NOT NULL,
            description_ar TEXT,
            description_en TEXT,
            price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            duration_days INTEGER,
            cashback_rate REAL DEFAULT 0.0,
            points_multiplier REAL DEFAULT 1.0,
            initial_points INTEGER DEFAULT 0,
            color_hex TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Membership plans table created")
    
    # 3. Create admin user
    print("\n👤 Creating admin user...")
    admin_id = str(uuid.uuid4())
    email = "admin@altayar.com"
    username = "admin"
    password = "Admin123"
    hashed_password = pwd_context.hash(password)
    
    cursor.execute("""
        INSERT INTO users (
            id, email, username, password_hash, 
            first_name, last_name, phone, role, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        admin_id,
        email,
        username,
        hashed_password,
        "System",
        "Admin",
        "+1234567890",
        "ADMIN",
        "ACTIVE"
    ))
    print("✓ Admin user created")
    
    conn.commit()
    
    print("\n" + "=" * 70)
    print("✅ Database initialized successfully!")
    print("=" * 70)
    print("\n🔐 Admin Login Credentials:")
    print("─" * 70)
    print(f"📧 Email:    {email}")
    print(f"👤 Username: {username}")
    print(f"🔑 Password: {password}")
    print("─" * 70)
    print("\n🚀 Next Steps:")
    print("  1. Start server: python server.py")
    print("  2. Login with admin credentials")
    print("  3. Create membership plans from admin panel")
    print("  4. Don't forget to set 'initial_points' for each plan!")
    
except sqlite3.IntegrityError as e:
    print(f"⚠️  Some data already exists: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
