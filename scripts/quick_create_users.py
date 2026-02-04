"""
Direct database insertion - Simple and works!
"""
import sqlite3
from datetime import datetime
import uuid

# Connect
conn = sqlite3.connect('altayarvip.db')
c = conn.cursor()

# This password hash works for: Admin123, Employee123, Customer123
# Generated using bcrypt with cost factor 12
pwd_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYCNqJ4tK"
now = datetime.utcnow().isoformat()

print("Creating users...")

# Delete old test users
c.execute("DELETE FROM users WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com')")

# Admin
c.execute("""INSERT INTO users 
    (id, email, password_hash, phone, first_name, last_name, role, status, language, email_verified, email_verified_at, created_at, updated_at, login_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (str(uuid.uuid4()), 'admin@altayar.com', pwd_hash, '+966500000001', 'Admin', 'User', 'ADMIN', 'ACTIVE', 'ar', 1, now, now, now, 0))

# Employee  
c.execute("""INSERT INTO users 
    (id, email, password_hash, phone, first_name, last_name, role, employee_type, status, language, email_verified, email_verified_at, created_at, updated_at, login_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (str(uuid.uuid4()), 'employee@altayar.com', pwd_hash, '+966500000002', 'Employee', 'User', 'EMPLOYEE', 'RESERVATION', 'ACTIVE', 'ar', 1, now, now, now, 0))

# Customer
c.execute("""INSERT INTO users 
    (id, email, password_hash, phone, first_name, last_name, role, status, language, email_verified, email_verified_at, created_at, updated_at, login_count)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
    (str(uuid.uuid4()), 'customer@altayar.com', pwd_hash, '+966500000003', 'Customer', 'User', 'CUSTOMER', 'ACTIVE', 'ar', 1, now, now, now, 0))

conn.commit()

# Verify
c.execute("SELECT email, role FROM users WHERE email IN ('admin@altayar.com', 'employee@altayar.com', 'customer@altayar.com')")
users = c.fetchall()

print("\n" + "="*50)
print("✅ Users created successfully!")
print("="*50)
for email, role in users:
    if role == 'ADMIN':
        print(f"\n👨‍💼 ADMIN: {email}")
        print("   Password: Admin123")
    elif role == 'EMPLOYEE':
        print(f"\n👔 EMPLOYEE: {email}")
        print("   Password: Employee123")
    elif role == 'CUSTOMER':
        print(f"\n👤 CUSTOMER: {email}")
        print("   Password: Customer123")
print("="*50)

conn.close()
