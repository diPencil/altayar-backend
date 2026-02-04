import requests

BASE_URL = "http://localhost:8082/api"

def test_endpoint(name, method, url, headers=None, data=None):
    print(f"Testing {name}...")
    try:
        if method == "GET":
            res = requests.get(url, headers=headers)
        elif method == "POST":
            res = requests.post(url, headers=headers, json=data)
        else:
            print(f"❌ Unsupported method: {method}")
            return False

        if res.status_code >= 200 and res.status_code < 300:
            print(f"✅ {name}: {res.status_code}")
            return True
        else:
            print(f"❌ {name}: {res.status_code} - {res.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ {name}: Exception - {e}")
        return False

# Login as admin
auth_res = requests.post(f"{BASE_URL}/auth/login", json={
    "identifier": "admin@altayar.com",
    "password": "Admin123"
})

if auth_res.status_code != 200:
    print(f"❌ Login failed: {auth_res.text}")
    exit(1)

token = auth_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print("🔧 Testing API Endpoints...\n")

# Test endpoints
tests = [
    ("GET /bookings", "GET", f"{BASE_URL}/bookings", headers),
    ("GET /bookings/me", "GET", f"{BASE_URL}/bookings/me", headers),
    ("GET /payments", "GET", f"{BASE_URL}/payments", headers),
    ("GET /payments/my-payments", "GET", f"{BASE_URL}/payments/my-payments", headers),
    ("GET /admin/users", "GET", f"{BASE_URL}/admin/users?limit=5", headers),
]

passed = 0
total = len(tests)

for name, method, url, headers in tests:
    if test_endpoint(name, method, url, headers):
        passed += 1

print("\n📊 Results:")
print(f"Passed: {passed}/{total}")
if passed == total:
    print("🎉 All endpoints are stable!")
else:
    print("⚠️ Some endpoints have issues.")
