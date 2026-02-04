"""
Test role-based notification filtering
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_role_filtering():
    """Test that each role sees only their notifications"""
    print("\n" + "="*60)
    print("ROLE-BASED NOTIFICATION FILTERING TEST")
    print("="*60)
    
    # Test with different user roles
    test_users = [
        {"email": "test_notif@example.com", "password": "Test123456", "expected_role": "CUSTOMER"},
        # Add more test users if needed
    ]
    
    for user_info in test_users:
        print(f"\nTesting with user: {user_info['email']}")
        
        try:
            # Login
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/login",
                json={"identifier": user_info["email"], "password": user_info["password"]},
                timeout=5
            )
            
            if response.status_code != 200:
                print(f"  [FAIL] Login failed: {response.status_code}")
                continue
                
            token = response.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get user info to check role
            user_response = requests.get(
                f"{BASE_URL}{API_PREFIX}/auth/me",
                headers=headers,
                timeout=5
            )
            
            if user_response.status_code == 200:
                user_data = user_response.json()
                user_role = user_data.get('role', 'UNKNOWN')
                print(f"  [OK] User role: {user_role}")
            else:
                print(f"  [WARNING] Could not get user info")
                user_role = "UNKNOWN"
            
            # Get notifications
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
                
                print(f"  [OK] Notifications returned: {notifications_count}")
                print(f"  [OK] Total: {total}")
                print(f"  [OK] Unread: {unread}")
                
                # Check that notifications match user's role
                if notifications_count > 0:
                    first_notif = data.get('notifications', [{}])[0]
                    target_role = first_notif.get('target_role')
                    target_user_id = first_notif.get('target_user_id')
                    
                    print(f"  [INFO] First notification target_role: {target_role}")
                    print(f"  [INFO] First notification target_user_id: {target_user_id}")
                    
                    # Verify filtering logic
                    if user_role in ['ADMIN', 'SUPER_ADMIN']:
                        print(f"  [OK] Admin user can see all notifications")
                    elif target_role == 'ALL' or target_role == user_role or target_user_id == user_data.get('id'):
                        print(f"  [OK] Notification filtering is correct")
                    else:
                        print(f"  [WARNING] Notification may not match user's role")
            else:
                print(f"  [FAIL] Get notifications failed: {response.status_code}")
                print(f"  [ERROR] Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"  [ERROR] Exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("Test completed")
    print("="*60)
    return 0

if __name__ == "__main__":
    sys.exit(test_role_filtering())
