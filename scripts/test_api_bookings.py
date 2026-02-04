"""
Quick test to call the bookings API directly and see the response
"""
import requests
import json

# Test admin bookings endpoint
print("=" * 60)
print("Testing Admin Bookings API")
print("=" * 60)

try:
    # You need to replace this with a valid admin token
    # Get it from the browser DevTools -> Application -> Local Storage
    token = "YOUR_ADMIN_TOKEN_HERE"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        "http://localhost:8082/api/bookings",
        headers=headers,
        timeout=5
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {response.headers}")
    print(f"\nResponse Body:")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Number of bookings: {len(data)}")
        print(f"\nFirst booking (if exists):")
        if data:
            print(json.dumps(data[0], indent=2))
        else:
            print("No bookings returned!")
    else:
        print(f"Error: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server!")
    print("Make sure server is running on port 8082")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Check server logs for:")
print("[list_all_bookings] Fetching bookings...")
print("[list_all_bookings] Found X bookings in database")
print("=" * 60)
