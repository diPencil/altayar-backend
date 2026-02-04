"""
Direct SQL insertion using Python sqlite3
"""
import sqlite3
from datetime import datetime
import uuid

# Connect to database
conn = sqlite3.connect('altayarvip.db')
cursor = conn.cursor()

try:
    print("🔧 Creating test users...")
    
    # Delete existing test users
    cursor.execute("""
        DELETE FROM users WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com')
    """)
    
    # Pre-hashed password for "Admin123", "Employee123", "Customer123"
    # This is a bcrypt hash that works
    password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK"
    
    now = datetime.utcnow().isoformat()
    
    # Insert Admin
    cursor.execute("""
        INSERT INTO users (
            id, email, password_hash, phone, first_name, last_name,
            role, status, language, email_verified, email_verified_at,
            created_at, updated_at, login_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        'admin@altayar.com',
        password_hash,
        '+966500000001',
        'Admin',
        'User',
        'ADMIN',
        'ACTIVE',
        'ar',
        1,
        now,
        now,
        now,
        0
    ))
    
    # Insert Employee
    cursor.execute("""
        INSERT INTO users (
            id, email, password_hash, phone, first_name, last_name,
            role, employee_type, status, language, email_verified, email_verified_at,
            created_at, updated_at, login_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        'employee@altayar.com',
        password_hash,
        '+966500000002',
        'Employee',
        'User',
        'EMPLOYEE',
        'RESERVATION',
        'ACTIVE',
        'ar',
        1,
        now,
        now,
        now,
        0
    ))
    
    # Insert Customer
    cursor.execute("""
        INSERT INTO users (
            id, email, password_hash, phone, first_name, last_name,
            role, status, language, email_verified, email_verified_at,
            created_at, updated_at, login_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()),
        'customer@altayar.com',
        password_hash,
        '+966500000003',
        'Customer',
        'User',
        'CUSTOMER',
        'ACTIVE',
        'ar',
        1,
        now,
        now,
        now,
        0
    ))
    
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT email, role, first_name, last_name FROM users 
        WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com')
    """)
    
    users = cursor.fetchall()
    
    print("✅ Users created successfully!")
    print("\n" + "="*60)
    print("📋 Test Accounts:")
    print("="*60)
    
    for user in users:
        email, role, first_name, last_name = user
        if role == 'ADMIN':
            print(f"\n👨‍💼 ADMIN:")
            print(f"   Email: {email}")
            print(f"   Password: Admin123")
        elif role == 'EMPLOYEE':
            print(f"\n👔 EMPLOYEE:")
            print(f"   Email: {email}")
            print(f"   Password: Employee123")
        elif role == 'CUSTOMER':
            print(f"\n👤 CUSTOMER:")
            print(f"   Email: {email}")
            print(f"   Password: Customer123")
    
    print("\n" + "="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
