import os
import sys

# Setup mock env
os.environ["DATABASE_URL"] = "sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db" 
os.environ["JWT_SECRET_KEY"] = "dummy"
os.environ["SECRET_KEY"] = "dummy"
os.environ["FAWATERK_API_KEY"] = "dummy"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy"

sys.path.append(os.path.join(os.path.dirname(__file__)))

# Import all models to register them with SQLAlchemy
import modules

from database.base import SessionLocal
from modules.auth.service import AuthService
from modules.auth.schemas import LoginRequest
import traceback

def debug_login():
    db = SessionLocal()
    try:
        print("Attempting login for admin@altayar.com...")
        service = AuthService(db)
        # Mock request object
        req = LoginRequest(email="admin@altayar.com", password="Admin123")
        
        user, access, refresh = service.login(req)
        print("LOGIN SUCCESS!")
        print(f"User: {user.email}")
        
    except Exception as e:
        print("LOGIN FAILED WITH ERROR:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    debug_login()
