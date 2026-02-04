import requests

BASE_URL = "http://localhost:8082/api"

# Login as admin
auth_res = requests.post(f"{BASE_URL}/auth/login", json={
    "identifier": "admin@altayar.com",
    "password": "Admin123"
})

if auth_res.status_code != 200:
    print(f"Login failed: {auth_res.text}")
    exit(1)

token = auth_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Get users
users_res = requests.get(f"{BASE_URL}/admin/users?limit=10", headers=headers)

if users_res.status_code != 200:
    print(f"Failed to get users: {users_res.text}")
    exit(1)

users = users_res.json().get('items', [])
print(f"Found {len(users)} users:")

for user in users:
    print(f"  {user['email']} - {user.get('role', 'unknown')}")
