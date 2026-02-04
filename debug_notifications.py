"""
Debug notification queries
"""
import sys
sys.path.insert(0, '.')

from database.base import SessionLocal
from modules.notifications.models import Notification, NotificationTargetRole
from modules.users.models import User
from sqlalchemy import or_

db = SessionLocal()

try:
    # Get a test user
    user = db.query(User).first()
    if not user:
        print("No users found in database")
        sys.exit(1)
    
    print(f"Testing with user: {user.id}, role: {user.role}")
    
    # Test the query logic
    target_role = None
    try:
        if hasattr(user, 'role') and user.role:
            role_value = user.role.value.upper()
            if role_value in NotificationTargetRole._member_names_:
                target_role = NotificationTargetRole(role_value)
    except (ValueError, AttributeError):
        pass
    
    print(f"Target role: {target_role}")
    
    # Build filter conditions
    filter_conditions = [
        Notification.target_user_id == user.id,
        Notification.target_role == NotificationTargetRole.ALL
    ]
    
    if target_role:
        filter_conditions.append(Notification.target_role == target_role)
    
    print(f"Filter conditions: {len(filter_conditions)}")
    
    # Test the query
    query = db.query(Notification).filter(or_(*filter_conditions))
    print(f"Query built successfully")
    
    # Try to execute
    notifications = query.all()
    print(f"Found {len(notifications)} notifications")
    
    # Test counting
    total_count = query.count()
    print(f"Total count: {total_count}")
    
    unread_count = query.filter(Notification.is_read == False).count()
    print(f"Unread count: {unread_count}")
    
    print("[OK] All queries executed successfully")
    
except Exception as e:
    print(f"[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    db.close()
