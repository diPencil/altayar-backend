import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__)))

# Set dummy env vars for Settings
os.environ["DATABASE_URL"] = "sqlite:///./altayarvip.db" 
os.environ["JWT_SECRET_KEY"] = "dummy"
os.environ["SECRET_KEY"] = "dummy"
os.environ["FAWATERK_API_KEY"] = "dummy"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy"

try:
    print("Attempting to import modules.wallet.routes...")
    from modules.wallet.routes import router as wallet_router
    print("✅ Wallet routes import successful!")

    print("Attempting to import modules.payments.routes...")
    from modules.payments.routes import router as payments_router
    print("✅ Payments routes import successful!")

    print("Attempting to import modules.admin.routes...")
    from modules.admin.routes import router as admin_router
    print("✅ Admin routes import successful!")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
