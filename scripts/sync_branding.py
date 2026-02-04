import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.base import SessionLocal
from modules.users.models import User, UserRole

def fix_branding_and_ids():
    db = SessionLocal()
    try:
        print("🔍 Scanning database for branding updates...")
        
        # 1. Fix Admin Name
        admins = db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN])).all()
        for admin in admins:
            print(f"👤 Updating admin: {admin.email} -> AltayarVIP")
            admin.first_name = "AltayarVIP"
            admin.last_name = ""
            admin.username = "AltayarVIP"
            
        # 2. Fix Membership IDs (Prefix with ALT- if missing)
        all_users = db.query(User).all()
        for user in all_users:
            current_id = user.membership_id_display
            if not current_id:
                # Use first 8 chars of UUID if missing
                current_id = f"ALT-{user.id[:8].upper()}"
                user.membership_id_display = current_id
                print(f"🆔 Generated ID for {user.email}: {current_id}")
            elif not str(current_id).startswith("ALT-"):
                new_id = f"ALT-{str(current_id).upper()}"
                user.membership_id_display = new_id
                print(f"🆔 Updated ID for {user.email}: {new_id}")

        db.commit()
        print("✅ Database branding and IDs synchronized successfully!")
        
    except Exception as e:
        print(f"❌ Error during update: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_branding_and_ids()
