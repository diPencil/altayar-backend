"""
Test bcrypt hash and verify
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.utils import hash_password, verify_password
import sqlite3

print("🧪 Testing password hash system...")
print("=" * 70)

# Test 1: Hash and verify in memory
password = "Admin123"
print(f"\n1️⃣ Testing hash_password() and verify_password()...")
print(f"   Password: {password}")

hashed = hash_password(password)
print(f"   Hash: {hashed[:50]}...")

result = verify_password(password, hashed)
print(f"   Verify result: {'✅ PASS' if result else '❌ FAIL'}")

if not result:
    print("\n❌ CRITICAL: hash_password/verify_password are broken!")
    exit(1)

# Test 2: Check what's in database
print(f"\n2️⃣ Checking database...")
conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

cursor.execute("SELECT email, password_hash FROM users WHERE email = 'admin@altayar.com'")
row = cursor.fetchone()

if row:
    email, db_hash = row
    print(f"   Found: {email}")
    print(f"   Hash in DB: {db_hash[:50]}...")
    
    # Test verify with DB hash
    db_result = verify_password(password, db_hash)
    print(f"   Verify DB hash: {'✅ PASS' if db_result else '❌ FAIL'}")
    
    if not db_result:
        print("\n❌ Problem: DB hash doesn't verify!")
        print("   The hash in database is corrupted or wrong.")
        print("\n🔧 Solution: Delete admin and recreate with correct hash")
        
        cursor.execute("DELETE FROM users WHERE email = 'admin@altayar.com'")
        conn.commit()
        print("   ✓ Deleted bad admin user")
        
        # Create new one with working hash
        import uuid
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
            admin_id, "admin@altayar.com", "admin", hashed,
            "System", "Admin", "+1234567890",
            "ADMIN", "ACTIVE", "ar", 1, 1, 0
        ))
        conn.commit()
        
        # Verify new one
        cursor.execute("SELECT password_hash FROM users WHERE email = 'admin@altayar.com'")
        new_hash = cursor.fetchone()[0]
        final_test = verify_password(password, new_hash)
        
        print(f"   ✓ Created new admin")
        print(f"   ✓ Final verification: {'✅ PASS' if final_test else '❌ FAIL'}")
        
        if final_test:
            print("\n" + "=" * 70)
            print("✅ FIXED! Admin user is now working!")
            print("=" * 70)
            print("\n🔐 Credentials:")
            print("   Email:    admin@altayar.com")
            print("   Password: Admin123")
            print("\n🚀 Start server and try login!")
    else:
        print("\n✅ Hash in database is correct!")
        print("   The problem might be elsewhere...")
else:
    print("   ❌ Admin user not found!")
    print("   Run: python final_admin.py")

conn.close()
