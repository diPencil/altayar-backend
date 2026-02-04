import sys
import os
import uuid
from datetime import datetime

# Add parent directory to path to allow importing modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole, UserStatus
from shared.utils import hash_password

def reset_admin_account():
    """
    Deletes ALL existing users and creates a single fresh Admin account.
    """
    db = SessionLocal()
    try:
        print("🗑️  Deleting all existing users...")
        # Delete all users
        try:
            db.query(User).delete()
            db.commit()
            print("✅ Users table cleared.")
        except Exception as e:
            print(f"⚠️  Could not clear table (might be empty or have FK constraints): {e}")
            db.rollback()

        print("👤 Creating fresh Admin account...")
        
        # Create fresh Admin
        new_admin = User(
            id=str(uuid.uuid4()),
            email="admin@altayar.com",
            # Hashing the password "admin123"
            password_hash=hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN,
            status=UserStatus.ACTIVE,
            language="ar",
            email_verified=True,
            email_verified_at=datetime.utcnow(),
            phone="+966599999999"
        )
        
        db.add(new_admin)
        db.commit()
        
        print("\n" + "="*60)
        print("✅ Fresh Admin Account Created Successfully!")
        print("="*60)
        print("📧 Email:    admin@altayar.com")
        print("🔑 Password: admin123")
        print("="*60)
        print("\nAll other default test accounts have been removed.")
        
    except Exception as e:
        print(f"❌ Error resetting admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_account()
