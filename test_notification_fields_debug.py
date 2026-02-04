"""
Debug why fields are missing from notification response
"""
import sys
sys.path.insert(0, '.')

from database.base import SessionLocal
from modules.notifications.models import Notification, NotificationTargetRole
from modules.users.models import User
from sqlalchemy import or_, desc

db = SessionLocal()

try:
    user = db.query(User).filter(User.email == 'test_notif@example.com').first()
    if not user:
        print("User not found")
        sys.exit(1)
    
    print(f"User: {user.email}, Role: {user.role}")
    
    # Get any notification from database
    notif = db.query(Notification).first()
    if not notif:
        print("No notifications found in database")
        sys.exit(1)
    
    print(f"\nNotification ID: {notif.id}")
    print(f"Has target_role: {hasattr(notif, 'target_role')}")
    if hasattr(notif, 'target_role'):
        print(f"  target_role value: {notif.target_role}")
        print(f"  target_role type: {type(notif.target_role)}")
        if hasattr(notif.target_role, 'value'):
            print(f"  target_role.value: {notif.target_role.value}")
        # Test conversion
        try:
            target_role_str = notif.target_role.value if hasattr(notif.target_role, 'value') else str(notif.target_role) if notif.target_role else None
            print(f"  target_role_str: {target_role_str}")
        except Exception as e:
            print(f"  Error converting target_role: {e}")
    
    print(f"\nHas target_user_id: {hasattr(notif, 'target_user_id')}")
    if hasattr(notif, 'target_user_id'):
        print(f"  target_user_id value: {notif.target_user_id}")
    
    print(f"\nHas updated_at: {hasattr(notif, 'updated_at')}")
    if hasattr(notif, 'updated_at'):
        print(f"  updated_at value: {notif.updated_at}")
        print(f"  updated_at type: {type(notif.updated_at)}")
        if notif.updated_at:
            try:
                updated_at_str = notif.updated_at.isoformat() if hasattr(notif.updated_at, 'isoformat') else str(notif.updated_at)
                print(f"  updated_at_str: {updated_at_str}")
            except Exception as e:
                print(f"  Error converting updated_at: {e}")
    
    # Test building notif_response like in routes.py
    print("\n--- Testing notif_response building ---")
    from datetime import datetime
    
    target_role_val = getattr(notif, 'target_role', None)
    target_role_str = target_role_val.value if hasattr(target_role_val, 'value') else str(target_role_val) if target_role_val else None
    print(f"target_role_str: {target_role_str}")
    
    updated_at_val = getattr(notif, 'updated_at', None)
    updated_at_str = updated_at_val.isoformat() if updated_at_val and hasattr(updated_at_val, 'isoformat') else (str(updated_at_val) if updated_at_val else None)
    print(f"updated_at_str: {updated_at_str}")
    
    notif_response = {
        "id": str(getattr(notif, 'id', '')),
        "target_role": target_role_str,
        "target_user_id": getattr(notif, 'target_user_id', None),
        "updated_at": updated_at_str,
    }
    
    print(f"\nnotif_response keys: {list(notif_response.keys())}")
    print(f"target_role in notif_response: {'target_role' in notif_response}, value: {notif_response.get('target_role')}")
    print(f"target_user_id in notif_response: {'target_user_id' in notif_response}, value: {notif_response.get('target_user_id')}")
    print(f"updated_at in notif_response: {'updated_at' in notif_response}, value: {notif_response.get('updated_at')}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
