"""
Debug script to check notification fields
"""
import sys
sys.path.insert(0, '.')

from database.base import SessionLocal
from modules.notifications.models import Notification
from modules.users.models import User

db = SessionLocal()

try:
    user = db.query(User).filter(User.email == 'test_notif@example.com').first()
    if not user:
        print("User not found")
        sys.exit(1)
    
    # Try to find any notification for this user (by user_id or ALL role)
    from modules.notifications.models import NotificationTargetRole
    from sqlalchemy import or_
    notif = db.query(Notification).filter(
        or_(
            Notification.target_user_id == user.id,
            Notification.target_role == NotificationTargetRole.ALL
        )
    ).first()
    if not notif:
        print("No notifications found")
        sys.exit(1)
    
    print(f"Notification ID: {notif.id}")
    print(f"Has target_role attribute: {hasattr(notif, 'target_role')}")
    if hasattr(notif, 'target_role'):
        print(f"  target_role value: {notif.target_role}")
        print(f"  target_role type: {type(notif.target_role)}")
        if hasattr(notif.target_role, 'value'):
            print(f"  target_role.value: {notif.target_role.value}")
    
    print(f"Has target_user_id attribute: {hasattr(notif, 'target_user_id')}")
    if hasattr(notif, 'target_user_id'):
        print(f"  target_user_id value: {notif.target_user_id}")
    
    print(f"Has updated_at attribute: {hasattr(notif, 'updated_at')}")
    if hasattr(notif, 'updated_at'):
        print(f"  updated_at value: {notif.updated_at}")
        print(f"  updated_at type: {type(notif.updated_at)}")
    
    # Test the code path
    target_role_val = getattr(notif, 'target_role', None)
    target_role_str = target_role_val.value if hasattr(target_role_val, 'value') else str(target_role_val) if target_role_val else None
    print(f"\nProcessed target_role_str: {target_role_str}")
    
    updated_at_val = getattr(notif, 'updated_at', None)
    updated_at_str = updated_at_val.isoformat() if updated_at_val and hasattr(updated_at_val, 'isoformat') else (str(updated_at_val) if updated_at_val else None)
    print(f"Processed updated_at_str: {updated_at_str}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
