"""
Complete admin user fix - delete and recreate with correct password
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole, UserStatus
from shared.utils import hash_password, verify_password
import uuid

print("🔧 Fixing admin user...")
print("=" * 70)

db = SessionLocal()

try:
    # Delete existing admin user
    existing = db.query(User).filter(User.email == "admin@altayar.com").first()
    if existing:
        print(f"🗑️  Deleting existing admin user: {existing.email}")
        db.delete(existing)
        db.commit()
    
    # Create fresh admin user
    password = "Admin123"
    hashed = hash_password(password)
    
    print(f"\n🔐 Creating new admin user...")
    print(f"   Password: {password}")
    print(f"   Hash: {hashed[:50]}...")
    
    # Verify hash works
    test_verify = verify_password(password, hashed)
    print(f"   Hash verification test: {'✅ PASS' if test_verify else '❌ FAIL'}")
    
    if not test_verify:
        print("\n❌ ERROR: Password hash verification failed!")
        print("   This is a critical error in the password hashing system.")
        exit(1)
    
    admin = User(
        id=str(uuid.uuid4()),
        email="admin@altayar.com",
        username="admin",
        password_hash=hashed,
        first_name="System",
        last_name="Admin",
        phone="+1234567890",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        email_verified=True,
        phone_verified=True,
        language="ar"
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    print(f"\n✅ Admin user created successfully!")
    print(f"   ID: {admin.id}")
    print(f"   Email: {admin.email}")
    print(f"   Role: {admin.role}")
    print(f"   Status: {admin.status}")
    
    # Final verification
    print(f"\n🔍 Final verification...")
    saved_user = db.query(User).filter(User.email == "admin@altayar.com").first()
    if saved_user:
        final_test = verify_password(password, saved_user.password_hash)
        print(f"   Password verification: {'✅ PASS' if final_test else '❌ FAIL'}")
        
        if final_test:
            print("\n" + "=" * 70)
            print("✅ SUCCESS! Admin user is ready!")
            print("=" * 70)
            print("\n🔐 Login Credentials:")
            print("   Email:    admin@altayar.com")
            print("   Password: Admin123")
            print("\n🚀 Start server: python server.py")
        else:
            print("\n❌ ERROR: Saved password hash doesn't verify!")
    else:
        print("\n❌ ERROR: Admin user not found after creation!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
