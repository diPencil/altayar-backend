"""
Create admin user using the EXACT same hash function as the server
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import uuid

# Import the EXACT same hash functions the server uses
from shared.utils import hash_password, verify_password

print("🔐 Creating admin user with server's hash function...")
print("=" * 70)

conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

try:
    # Delete existing admin
    cursor.execute("DELETE FROM users WHERE email = 'admin@altayar.com'")
    if cursor.rowcount > 0:
        print("🗑️  Deleted existing admin user")
    
    # Create password hash using SERVER'S function
    password = "Admin123"
    hashed = hash_password(password)
    
    print(f"\n🔐 Creating admin user...")
    print(f"   Email: admin@altayar.com")
    print(f"   Password: {password}")
    print(f"   Using server's hash_password() function")
    
    # Test hash immediately
    test_verify = verify_password(password, hashed)
    print(f"   Hash test: {'✅ PASS' if test_verify else '❌ FAIL'}")
    
    if not test_verify:
        print("\n❌ CRITICAL ERROR: Hash function not working!")
        exit(1)
    
    # Insert admin
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
    
    conn.commit()
    
    # Verify saved data
    cursor.execute("SELECT email, password_hash, role, status FROM users WHERE email = 'admin@altayar.com'")
    result = cursor.fetchone()
    
    if result:
        email, saved_hash, role, status = result
        print(f"\n✅ Admin user created!")
        print(f"   Email: {email}")
        print(f"   Role: {role}")
        print(f"   Status: {status}")
        
        # Final verification with saved hash
        final_test = verify_password(password, saved_hash)
        print(f"\n🔍 Final password verification: {'✅ PASS' if final_test else '❌ FAIL'}")
        
        if final_test:
            print("\n" + "=" * 70)
            print("✅ SUCCESS! Admin is ready!")
            print("=" * 70)
            print("\n🔐 Login Credentials:")
            print("   📧 Email:    admin@altayar.com")
            print("   🔑 Password: Admin123")
            print("\n🚀 Now start server: python server.py")
            print("   Then login with the credentials above!")
        else:
            print("\n❌ ERROR: Saved hash doesn't verify!")
            print("   This shouldn't happen - please report this issue.")
    else:
        print("\n❌ ERROR: Admin not found after creation!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
