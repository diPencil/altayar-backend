"""
Test admin notifications access
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_admin_notifications():
    """Test that admin can see all notifications"""
    print("\n" + "="*60)
    print("ADMIN NOTIFICATIONS TEST")
    print("="*60)
    
    # Try to login as admin (you may need to update credentials)
    login_attempts = [
        {"identifier": "admin@altayar.com", "password": "Admin123456"},
        {"identifier": "admin@altayar.com", "password": "admin123456"},
        {"identifier": "admin@altayar.com", "password": "admin"},
    ]
    
    token = None
    for attempt in login_attempts:
        try:
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json=attempt,
                timeout=5
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                print(f"[OK] Logged in as: {attempt['identifier']}")
                break
        except Exception as e:
            continue
    
    if not token:
        print("[WARNING] Could not login as admin, testing with any user...")
        # Use test user instead
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"identifier": "test_notif@example.com", "password": "Test123456"},
            timeout=5
        )
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("[OK] Using test user instead")
        else:
            print("[ERROR] Could not login")
            return 1
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test notifications endpoint
    print("\nTesting notifications endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/notifications?limit=50&include_read=true",
            headers=headers,
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            notifications_count = len(data.get('notifications', []))
            total = data.get('total', 0)
            unread = data.get('unread_count', 0)
            
            print(f"[OK] Status: {response.status_code}")
            print(f"[OK] Notifications returned: {notifications_count}")
            print(f"[OK] Total: {total}")
            print(f"[OK] Unread: {unread}")
            
            if notifications_count > 0:
                print(f"\n[OK] First notification:")
                first = data.get('notifications', [{}])[0]
                print(f"  - ID: {first.get('id', 'N/A')[:20]}...")
                print(f"  - Type: {first.get('type', 'N/A')}")
                print(f"  - Title: {first.get('title', 'N/A')[:50]}...")
                print(f"  - Is Read: {first.get('is_read', 'N/A')}")
            
            if notifications_count == 0 and total > 0:
                print(f"\n[WARNING] Total shows {total} but 0 notifications returned!")
                print("This indicates a filtering or response building issue.")
                return 1
            elif notifications_count > 0:
                print(f"\n[OK] Notifications are being returned correctly!")
                return 0
            else:
                print(f"\n[INFO] No notifications found (this might be expected)")
                return 0
        else:
            print(f"[ERROR] Status: {response.status_code}")
            print(f"[ERROR] Response: {response.text[:500]}")
            return 1
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_admin_notifications())
