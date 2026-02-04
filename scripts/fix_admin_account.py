import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))


# Set dummy env vars to bypass Pydantic validation
os.environ["DATABASE_URL"] = "sqlite:///./altayarvip.db" 
os.environ["JWT_SECRET_KEY"] = "dummy_jwt_secret"
os.environ["SECRET_KEY"] = "dummy_secret"
os.environ["FAWATERK_API_KEY"] = "dummy_key"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy_key"

from database.base import SessionLocal
from modules.users.models import User, UserStatus, UserRole
from shared.utils import hash_password
from datetime import datetime

def fix_admin():
    db = SessionLocal()
    try:
        email = "admin@altayar.com"
        password = "Admin123"
        
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"User {email} not found! Creating it...")
            new_admin = User(
                email=email,
                password_hash=hash_password(password),
                first_name="Admin",
                last_name="User",
                role=UserRole.ADMIN,
                status=UserStatus.ACTIVE,
                email_verified=True,
                email_verified_at=datetime.utcnow(),
                language="ar"
            )
            db.add(new_admin)
            db.commit()
            print(f"✅ Created Admin user: {email}")
        else:
            print(f"Found user: {user.email}, Role: {user.role}, Status: {user.status}")
            
            needs_update = False
            if user.role != UserRole.ADMIN:
                user.role = UserRole.ADMIN
                needs_update = True
                print("Updated role to ADMIN")
                
            if user.status != UserStatus.ACTIVE:
                user.status = UserStatus.ACTIVE
                needs_update = True
                print("Updated status to ACTIVE")
                
            # Optional: Reset password if requested, but for now verify existence
            # user.password_hash = get_password_hash(password)
            
            if needs_update:
                db.commit()
                print("✅ Updated Admin user details")
            else:
                print("✅ Admin user is already correct.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin()
