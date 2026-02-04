"""
Test Notifications with Authentication
Creates a test user, logs in, and tests notification endpoints
"""
import requests
import sys
import json

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_with_auth():
    """Test notifications with authentication"""
    print("\n" + "="*60)
    print("NOTIFICATION ENDPOINTS TEST (WITH AUTH)")
    print("="*60)
    
    # Step 1: Login with test user
    print("\n1. Logging in...")
    login_data = {
        "identifier": "test_notif@example.com",
        "password": "Test123456"
    }
    
    try:
        # Try to login first
        login_response = requests.post(
            f"{BASE_URL}{API_PREFIX}/auth/login",
            json=login_data,
            timeout=5
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("access_token")
            print("[OK] User logged in")
        else:
            # Try to register if login fails
            print("[INFO] Login failed, trying to register...")
            register_data = {
                "username": "test_notif_user",
                "email": "test_notif@example.com",
                "password": "Test123456",
                "first_name": "Test",
                "last_name": "User"
            }
            response = requests.post(
                f"{BASE_URL}{API_PREFIX}/auth/register",
                json=register_data,
                timeout=5
            )
            
            if response.status_code in [200, 201]:
                print("[OK] User registered, now logging in...")
                login_response = requests.post(
                    f"{BASE_URL}{API_PREFIX}/auth/login",
                    json=login_data,
                    timeout=5
                )
                if login_response.status_code == 200:
                    token = login_response.json().get("access_token")
                    print("[OK] User logged in")
                else:
                    print(f"[ERROR] Login failed: {login_response.status_code}")
                    return 1
            else:
                print(f"[ERROR] Registration failed: {response.status_code} - {response.text[:200]}")
                return 1
    except Exception as e:
        print(f"[ERROR] Auth error: {str(e)[:200]}")
        return 1
    
    if not token:
        print("[ERROR] No token received")
        return 1
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Test notification endpoints
    print("\n2. Testing notification endpoints...")
    
    endpoints = [
        ("GET", f"{API_PREFIX}/notifications", "Get notifications"),
        ("GET", f"{API_PREFIX}/notifications/stats", "Get stats"),
        ("GET", f"{API_PREFIX}/notifications/unread-count", "Get unread count"),
    ]
    
    results = []
    for method, endpoint, description in endpoints:
        try:
            url = f"{BASE_URL}{endpoint}"
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                print(f"[OK] {description}: 200 OK")
                if "notifications" in data:
                    print(f"      Found {len(data.get('notifications', []))} notifications")
                if "unread_count" in data:
                    print(f"      Unread count: {data.get('unread_count', 0)}")
                results.append(True)
            else:
                print(f"[FAIL] {description}: {response.status_code} - {response.text[:200]}")
                results.append(False)
        except Exception as e:
            print(f"[ERROR] {description}: {str(e)[:200]}")
            results.append(False)
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("[OK] All notification endpoints work correctly with authentication")
        return 0
    else:
        print("[WARNING] Some endpoints failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_with_auth())
