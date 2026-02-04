"""
Test API Endpoints
Verifies that all critical endpoints are accessible
"""
import requests
import sys
import time
from typing import List, Tuple

BASE_URL = "http://127.0.0.1:8082"
API_PREFIX = "/api"

def test_endpoint(method: str, endpoint: str, expected_status: int = 200, data: dict = None, headers: dict = None) -> Tuple[bool, str]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=5)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers, timeout=5)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers, timeout=5)
        else:
            return False, f"Unknown method: {method}"
        
        # Check if status matches expected (or is in acceptable range)
        if isinstance(expected_status, list):
            is_ok = response.status_code in expected_status
        else:
            is_ok = response.status_code == expected_status
        
        if is_ok:
            return True, f"Status {response.status_code}"
        else:
            return False, f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - server may not be running"
    except requests.exceptions.Timeout:
        return False, "Request timeout"
    except Exception as e:
        return False, f"Error: {str(e)[:200]}"

def main():
    """Run endpoint tests"""
    print("\n" + "="*60)
    print("API ENDPOINT TESTS")
    print("="*60)
    
    # Wait a moment for server to be ready
    print("\nWaiting for server to be ready...")
    time.sleep(2)
    
    # Test basic endpoints (no auth required)
    print("\n1. Testing Basic Endpoints (No Auth Required)")
    print("-" * 60)
    
    basic_tests = [
        ("GET", "/", 200, "Root endpoint"),
        ("GET", "/health", 200, "Health check"),
        ("GET", "/docs", 200, "API documentation"),
        ("GET", "/openapi.json", 200, "OpenAPI schema"),
    ]
    
    basic_results = []
    for method, endpoint, expected_status, description in basic_tests:
        success, message = test_endpoint(method, endpoint, expected_status)
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {description}: {message}")
        basic_results.append((success, description))
    
    # Test API endpoints (may require auth, but should return proper errors)
    print("\n2. Testing API Endpoints (Auth May Be Required)")
    print("-" * 60)
    
    api_tests = [
        ("GET", f"{API_PREFIX}/auth/me", [200, 401], "Get current user"),
        ("GET", f"{API_PREFIX}/notifications", [200, 401], "Get notifications"),
        ("GET", f"{API_PREFIX}/notifications/stats", [200, 401], "Notification stats"),
        ("GET", f"{API_PREFIX}/notifications/unread-count", [200, 401], "Unread count"),
        ("GET", f"{API_PREFIX}/offers/public", 200, "Public offers"),
        ("GET", f"{API_PREFIX}/offers/public/featured", 200, "Featured offers"),
        ("GET", f"{API_PREFIX}/offers/categories", [200, 401], "Offer categories"),
        ("GET", f"{API_PREFIX}/memberships/plans", 200, "Membership plans"),
    ]
    
    api_results = []
    for method, endpoint, expected_status, description in api_tests:
        success, message = test_endpoint(method, endpoint, expected_status)
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {description}: {message}")
        api_results.append((success, description))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    basic_passed = sum(1 for success, _ in basic_results if success)
    api_passed = sum(1 for success, _ in api_results if success)
    
    print(f"\nBasic Endpoints: {basic_passed}/{len(basic_results)} passed")
    print(f"API Endpoints: {api_passed}/{len(api_results)} passed")
    print(f"Total: {basic_passed + api_passed}/{len(basic_results) + len(api_results)} passed")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print("\n[OK] Server is running and responding")
        else:
            print(f"\n[WARNING] Server responded with status {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Server is not running or not accessible")
        print("Please start the server using: python server.py")
        return 1
    
    if basic_passed + api_passed == len(basic_results) + len(api_results):
        print("\n[OK] All endpoint tests passed!")
        return 0
    else:
        print("\n[WARNING] Some endpoints failed. Check server logs for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
