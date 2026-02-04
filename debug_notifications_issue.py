"""
Debug why notifications are empty
"""
import sys
sys.path.insert(0, '.')

from database.base import SessionLocal
from modules.notifications.models import Notification, NotificationTargetRole
from modules.users.models import User
from sqlalchemy import or_, desc

db = SessionLocal()

try:
    # Get test user
    user = db.query(User).filter(User.email == 'test_notif@example.com').first()
    if not user:
        print("User not found")
        sys.exit(1)
    
    print(f"User: {user.id}, Role: {user.role}")
    
    # Get target role
    target_role = None
    try:
        if hasattr(user, 'role') and user.role:
            role_value = user.role.value.upper()
            if role_value in NotificationTargetRole._member_names_:
                target_role = NotificationTargetRole(role_value)
    except (ValueError, AttributeError):
        pass
    
    print(f"Target role: {target_role}")
    
    # Build filter
    filter_conditions = [
        Notification.target_user_id == user.id,
        Notification.target_role == NotificationTargetRole.ALL
    ]
    
    if target_role:
        filter_conditions.append(Notification.target_role == target_role)
    
    query = db.query(Notification).filter(or_(*filter_conditions))
    
    # Try to get notifications
    print("\nTrying to get notifications...")
    try:
        notifications = query.order_by(desc(Notification.created_at)).limit(10).all()
        print(f"Found {len(notifications)} notifications")
        
        for i, notif in enumerate(notifications[:3]):
            print(f"\nNotification {i+1}:")
            print(f"  ID: {notif.id}")
            print(f"  Type: {notif.type} (type: {type(notif.type)})")
            try:
                print(f"  Type value: {notif.type.value}")
            except Exception as e:
                print(f"  Type value error: {e}")
            print(f"  Title: {notif.title[:50]}")
            print(f"  Is read: {notif.is_read}")
            
            # Try to build response
            try:
                notif_type = notif.type.value if hasattr(notif.type, 'value') else str(notif.type)
                print(f"  Processed type: {notif_type}")
            except Exception as e:
                print(f"  Processing error: {e}")
                import traceback
                traceback.print_exc()
    except Exception as e:
        print(f"Error getting notifications: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
