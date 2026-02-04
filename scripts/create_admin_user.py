"""
Create admin user using SQLAlchemy models
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole, UserStatus
from passlib.context import CryptContext
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("🔐 Creating admin user with SQLAlchemy...")
print("=" * 70)

db = SessionLocal()

try:
    # Check if admin exists
    existing = db.query(User).filter(User.email == "admin@altayar.com").first()
    
    if existing:
        print("⚠️  Admin user already exists!")
        print(f"   Email: {existing.email}")
        print(f"   Role: {existing.role}")
        print("\n🔄 Updating password...")
        
        # Update password
        existing.password_hash = pwd_context.hash("Admin123")
        db.commit()
        print("✅ Password updated!")
    else:
        # Create new admin
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@altayar.com",
            username="admin",
            password_hash=pwd_context.hash("Admin123"),
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
        print("✅ Admin user created!")
    
    print("\n" + "=" * 70)
    print("🔐 Admin Credentials:")
    print("─" * 70)
    print("📧 Email:    admin@altayar.com")
    print("👤 Username: admin")
    print("🔑 Password: Admin123")
    print("=" * 70)
    print("\n🚀 Now start the server: python server.py")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
