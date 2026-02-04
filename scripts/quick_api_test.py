"""
Test the actual API endpoint to see the exact error
"""
import requests

print("Testing bookings API...")
print("=" * 60)

try:
    # Test without auth first to see if server responds
    response = requests.get(
        "http://localhost:8082/api/bookings/debug/count",
        timeout=5
    )
    
    print(f"Debug endpoint status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    
except requests.exceptions.ConnectionError:
    print("❌ Server not running on port 8082!")
    print("Start it with: python server.py")
except Exception as e:
    print(f"Error: {e}")

print("=" * 60)
