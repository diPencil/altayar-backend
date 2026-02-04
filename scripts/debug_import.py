import sys
import os

# Add backend directory to path
sys.path.append(os.getcwd())

try:
    print("Attempting to import modules.bookings.routes...")
    from modules.bookings.routes import router
    print("✅ Verified: modules.bookings.routes imported successfully.")
except Exception as e:
    print(f"❌ Import Failed: {e}")
    import traceback
    traceback.print_exc()
