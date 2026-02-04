import os
import sys

# Set dummy env vars to bypass Pydantic validation
os.environ["DATABASE_URL"] = "sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db"
os.environ["JWT_SECRET_KEY"] = "dummy_jwt_secret"
os.environ["SECRET_KEY"] = "dummy_secret"
os.environ["FAWATERK_API_KEY"] = "dummy_key"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy_key"

sys.path.append(os.path.join(os.path.dirname(__file__)))

from database.base import SessionLocal
from modules.users.models import User
from shared.utils import hash_password

def check_user():
    db = SessionLocal()
    try:
        email = "admin@altayar.com"
        print(f"Checking user: {email}...")
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"✅ User FOUND: {user.email}")
            print(f"Role: {user.role}")
            print(f"Status: {user.status}")
            
            # Reset password
            print("Resetting password to 'Admin123'...")
            user.password_hash = hash_password("Admin123")
            db.commit()
            print("✅ Password reset successfully!")
        else:
            print(f"❌ User NOT FOUND: {email}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_user()
