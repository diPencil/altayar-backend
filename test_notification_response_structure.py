"""
Test notification response structure matches frontend expectations
"""
import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_response_structure():
    """Test that the response structure matches frontend expectations"""
    print("\n" + "="*60)
    print("NOTIFICATION RESPONSE STRUCTURE TEST")
    print("="*60)
    
    # Login
    try:
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json={"identifier": "test_notif@example.com", "password": "Test123456"},
            timeout=5
        )
        if response.status_code != 200:
            print(f"[ERROR] Login failed: {response.status_code}")
            return 1
        token = response.json().get("access_token")
        print("[OK] Logged in successfully")
    except Exception as e:
        print(f"[ERROR] Login exception: {e}")
        return 1
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get notifications
    try:
        response = requests.get(
            f"{BASE_URL}{API_PREFIX}/notifications?limit=50&include_read=true",
            headers=headers,
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"[ERROR] Get notifications failed: {response.status_code}")
            print(f"[ERROR] Response: {response.text[:500]}")
            return 1
        
        data = response.json()
        
        # Check top-level structure
        print("\n[CHECK] Top-level structure:")
        required_keys = ['notifications', 'total', 'unread_count']
        for key in required_keys:
            has_key = key in data
            print(f"  [{'OK' if has_key else 'MISSING'}] {key}: {has_key}")
            if not has_key:
                print(f"    [ERROR] Missing required key: {key}")
                return 1
        
        # Check notifications array
        notifications = data.get('notifications', [])
        print(f"\n[CHECK] Notifications array:")
        print(f"  [OK] Is array: {isinstance(notifications, list)}")
        print(f"  [OK] Count: {len(notifications)}")
        
        if len(notifications) == 0:
            print(f"  [WARNING] No notifications returned!")
            print(f"  [INFO] Total in response: {data.get('total', 0)}")
            print(f"  [INFO] Unread count: {data.get('unread_count', 0)}")
            return 1
        
        # Check first notification structure
        first_notif = notifications[0]
        print(f"\n[CHECK] First notification structure:")
        
        # Required fields for frontend
        required_fields = [
            'id', 'type', 'title', 'message', 'is_read', 'created_at',
            'related_entity_id', 'related_entity_type', 'target_role',
            'target_user_id', 'updated_at', 'priority', 'action_url'
        ]
        
        missing_fields = []
        for field in required_fields:
            has_field = field in first_notif
            status = '[OK]' if has_field else '[MISSING]'
            print(f"  {status} {field}: {has_field}")
            if not has_field:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n[ERROR] Missing fields: {missing_fields}")
            print(f"[INFO] Available fields: {list(first_notif.keys())}")
            return 1
        
        # Check data types
        print(f"\n[CHECK] Data types:")
        print(f"  [OK] id is string: {isinstance(first_notif.get('id'), str)}")
        print(f"  [OK] type is string: {isinstance(first_notif.get('type'), str)}")
        print(f"  [OK] is_read is bool: {isinstance(first_notif.get('is_read'), bool)}")
        print(f"  [OK] created_at is string: {isinstance(first_notif.get('created_at'), str)}")
        
        print(f"\n[OK] Response structure is correct!")
        print(f"[OK] Returning {len(notifications)} notifications")
        return 0
        
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(test_response_structure())
