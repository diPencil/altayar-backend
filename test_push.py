#!/usr/bin/env python3
"""
Test script to send push notifications
Usage: python test_push.py <user_email>
"""
import sys
from database.base import SessionLocal
from modules.notifications.service import NotificationService
from modules.users.models import User

def send_test_notification(user_email: str):
    """Send a test push notification to a user"""
    db = SessionLocal()
    
    try:
        # Find user
        user = db.query(User).filter(User.email == user_email).first()
        
        if not user:
            print(f"❌ User not found: {user_email}")
            return
        
        # Check if user has push token
        if not user.expo_push_token:
            print(f"❌ User {user_email} doesn't have a push token")
            print("   Make sure the user has logged in to the app")
            return
        
        print(f"✅ Found user: {user.email}")
        print(f"📱 Push token: {user.expo_push_token}")
        
        # Send test notification
        service = NotificationService(db)
        
        print("\n📤 Sending test notification...")
        service.send_push_notification(
            user_id=user.id,
            title="🎉 Test Notification",
            body="لو شفت الرسالة دي، يبقى Push Notifications شغالة!",
            data={"url": "/(user)/profile"}
        )
        
        print("✅ Notification sent successfully!")
        print("\n📱 Check your phone for the notification")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_push.py <user_email>")
        print("Example: python test_push.py user@example.com")
        sys.exit(1)
    
    user_email = sys.argv[1]
    send_test_notification(user_email)
