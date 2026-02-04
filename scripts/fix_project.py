"""
MASTER FIX SCRIPT
1. Connects to the CORRECT database file (altayarvip.db)
2. Drops and recreates all tables
3. Creates Admin User (with correct password hash)
4. Creates Membership Plans (with initial_points)
"""
import sys
import os
import sqlite3
import uuid
from datetime import datetime

# Add backend to path to import utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.utils import hash_password, verify_password

# CORRECT DATABASE PATH from settings.py
DB_PATH = "d:/Development/altayar/MobileApp/backend/altayarvip.db"

print(f"🚀 Starting Master Fix on: {DB_PATH}")
print("=" * 70)

# Delete old DB if exists to start fresh
if os.path.exists(DB_PATH):
    try:
        os.remove(DB_PATH)
        print("✓ Removed old database file")
    except Exception as e:
        print(f"⚠️ Could not delete old file: {e}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 1. Create Tables
    print("\n📋 Creating Tables...")
    
    # Users Table
    cursor.execute("""
        CREATE TABLE users (
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
    
    # Membership Plans Table
    cursor.execute("""
        CREATE TABLE membership_plans (
            id TEXT PRIMARY KEY,
            tier_code TEXT UNIQUE NOT NULL,
            tier_name_ar TEXT NOT NULL,
            tier_name_en TEXT NOT NULL,
            tier_order INTEGER NOT NULL,
            description_ar TEXT,
            description_en TEXT,
            price REAL DEFAULT 0.0,
            currency TEXT DEFAULT 'USD',
            plan_type TEXT,
            duration_days INTEGER,
            purchase_limit INTEGER,
            cashback_rate REAL DEFAULT 0.0,
            points_multiplier REAL DEFAULT 1.0,
            initial_points INTEGER DEFAULT 0,
            perks TEXT,
            upgrade_criteria TEXT,
            color_hex TEXT,
            icon_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("✓ Membership plans table created")

    # 2. Create Admin User
    print("\n👤 Creating Admin User...")
    
    password = "Admin123"
    hashed = hash_password(password)
    
    # Verify hash works
    if not verify_password(password, hashed):
        print("❌ Hashing failed internally!")
        exit(1)
        
    admin_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO users (
            id, email, username, password_hash,
            first_name, last_name, phone,
            role, status, language,
            email_verified, phone_verified,
            login_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, (
        admin_id,
        "admin@altayar.com",
        "admin",
        hashed,
        "System",
        "Admin",
        "+1234567890",
        "ADMIN",
        "ACTIVE",
        "ar",
        1,
        1,
        0
    ))
    print("✓ Admin user created")

    # 3. Create Membership Plans
    print("\n💎 Creating Membership Plans...")
    memberships = [
        ("BRONZE", "برونزي", "Bronze", 1, 1000.00, 1000, 0.02, 1.0, "#CD7F32"),
        ("SILVER", "فضي", "Silver", 2, 2000.00, 1500, 0.03, 1.2, "#C0C0C0"),
        ("GOLD", "ذهبي", "Gold", 3, 5000.00, 4000, 0.05, 1.5, "#FFD700"),
        ("PLATINUM", "بلاتيني", "Platinum", 4, 10000.00, 8500, 0.07, 2.0, "#E5E4E2"),
        ("VIP", "في آي بي", "VIP", 5, 20000.00, 18000, 0.10, 2.5, "#9B59B6"),
        ("DIAMOND", "ماسي", "Diamond", 6, 50000.00, 47000, 0.15, 3.0, "#B9F2FF")
    ]
    
    for tier_code, name_ar, name_en, order, price, points, cashback, multiplier, color in memberships:
        cursor.execute("""
            INSERT INTO membership_plans (
                id, tier_code, tier_name_ar, tier_name_en, tier_order,
                price, initial_points, currency, duration_days,
                cashback_rate, points_multiplier, color_hex, is_active
            ) VALUES (
                lower(hex(randomblob(16))), ?, ?, ?, ?, ?, ?, 'USD', 365, ?, ?, ?, 1
            )
        """, (tier_code, name_ar, name_en, order, price, points, cashback, multiplier, color))
    print("✓ Membership plans created")

    conn.commit()
    
    print("\n" + "=" * 70)
    print("✅ MASTER FIX COMPLETED SUCESSFULLY!")
    print("=" * 70)
    print("\n📝 Database: altayarvip.db (Correct File)")
    print("\n🔐 Login Credentials:")
    print("   Email:    admin@altayar.com")
    print("   Password: Admin123")
    print("\n🚀 You can now start the server!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    conn.close()
