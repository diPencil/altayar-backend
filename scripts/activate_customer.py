import os

# Set dummy env vars to bypass Pydantic validation
# We set them unconditionally to ensure they exist before config imports
os.environ["DATABASE_URL"] = "sqlite:///./altayarvip.db" 
os.environ["JWT_SECRET_KEY"] = "dummy_jwt_secret"
os.environ["SECRET_KEY"] = "dummy_secret"
os.environ["FAWATERK_API_KEY"] = "dummy_key"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy_key"


from database.base import SessionLocal
from modules.users.models import User, UserStatus
from datetime import datetime

def activate_customer():
    db = SessionLocal()
    try:
        email = "customer@altayar.com"
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"User {email} not found!")
            return

        print(f"Found user: {user.email}, Role: {user.role}, Status: {user.status}")
        
        # Verify and Activate
        user.status = UserStatus.ACTIVE
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        user.phone_verified = True
        user.phone_verified_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        print(f"✅ User {user.email} is now ACTIVE and VERIFIED.")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    activate_customer()
