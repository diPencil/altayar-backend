"""
Test Notifications Endpoints
"""
import requests
import sys

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_notification_endpoints():
    """Test notification endpoints"""
    print("\n" + "="*60)
    print("NOTIFICATION ENDPOINTS TEST")
    print("="*60)
    
    # Test endpoints that should return 401 (no auth)
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
                response = requests.get(url, timeout=5)
            
            if response.status_code == 401:
                print(f"[OK] {description}: 401 Unauthorized (expected)")
                results.append(True)
            elif response.status_code == 200:
                print(f"[OK] {description}: 200 OK")
                results.append(True)
            else:
                print(f"[FAIL] {description}: {response.status_code} - {response.text[:200]}")
                results.append(False)
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] {description}: Connection refused - server not running")
            results.append(False)
        except Exception as e:
            print(f"[ERROR] {description}: {str(e)[:200]}")
            results.append(False)
    
    print("\n" + "="*60)
    print(f"Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("[OK] All notification endpoints are accessible")
        return 0
    else:
        print("[WARNING] Some endpoints failed")
        return 1

if __name__ == "__main__":
    sys.exit(test_notification_endpoints())
