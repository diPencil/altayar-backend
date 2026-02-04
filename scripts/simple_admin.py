"""
Simple admin user creation using direct SQL
"""
import sqlite3
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("🔐 Creating admin user with direct SQL...")
print("=" * 70)

conn = sqlite3.connect('altayar.db')
cursor = conn.cursor()

try:
    # Delete existing admin
    cursor.execute("DELETE FROM users WHERE email = 'admin@altayar.com'")
    if cursor.rowcount > 0:
        print("🗑️  Deleted existing admin user")
    
    # Create new admin
    admin_id = str(uuid.uuid4())
    password = "Admin123"
    hashed = pwd_context.hash(password)
    
    print(f"\n🔐 Creating admin user...")
    print(f"   Email: admin@altayar.com")
    print(f"   Password: {password}")
    
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
    
    # Verify
    cursor.execute("SELECT email, role, status FROM users WHERE email = 'admin@altayar.com'")
    result = cursor.fetchone()
    
    if result:
        print(f"\n✅ Admin user created successfully!")
        print(f"   Email: {result[0]}")
        print(f"   Role: {result[1]}")
        print(f"   Status: {result[2]}")
        
        # Test password
        cursor.execute("SELECT password_hash FROM users WHERE email = 'admin@altayar.com'")
        saved_hash = cursor.fetchone()[0]
        test_verify = pwd_context.verify(password, saved_hash)
        
        print(f"\n🔍 Password verification: {'✅ PASS' if test_verify else '❌ FAIL'}")
        
        if test_verify:
            print("\n" + "=" * 70)
            print("✅ SUCCESS! You can now login!")
            print("=" * 70)
            print("\n🔐 Credentials:")
            print("   📧 Email:    admin@altayar.com")
            print("   🔑 Password: Admin123")
            print("\n🚀 Start server: python server.py")
        else:
            print("\n❌ ERROR: Password verification failed!")
    else:
        print("\n❌ ERROR: Admin user not found after creation!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
