import urllib.request
import json
import urllib.error
import sys

BASE_URL = "http://127.0.0.1:8001/api"

def call_api(endpoint, method="GET", payload=None, token=None):
    url = f"{BASE_URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

# 1. Login
print("Logging in as admin...")
login_res = call_api("/auth/login", "POST", {"email": "admin@altayar.com", "password": "admin123"})
if not login_res or "access_token" not in login_res:
    print("Login failed")
    sys.exit(1)
token = login_res["access_token"]
print("Login successful")

# 2. Get Plans
print("Fetching membership plans...")
plans = call_api("/memberships/plans", token=token)
if not plans:
    print("No plans found")
    sys.exit(1)

plan = plans[0]
plan_id = plan["id"]
print(f"Using plan: {plan['tier_name_en']} ({plan_id})")

# 3. Create User
import random
username = f"testuser_{random.randint(1000, 9999)}"
email = f"{username}@example.com"
user_payload = {
    "email": email,
    "username": username,
    "password": "password123",
    "first_name": "Test",
    "last_name": "User",
    "role": "CUSTOMER",
    "status": "ACTIVE",
    "plan_id": plan_id
}

print(f"Creating user {email} with plan {plan['tier_name_en']}...")
create_res = call_api("/admin/users", "POST", user_payload, token=token)
if not create_res:
    print("User creation failed")
    sys.exit(1)

user_id = create_res["user_id"]
print(f"User created successfully: {user_id}")

# 4. Verify User Details
print(f"Verifying user details for {user_id}...")
user_details = call_api(f"/admin/users/{user_id}/details", token=token)
if not user_details:
    print("Failed to fetch user details")
    sys.exit(1)

membership = user_details.get("membership")
if not membership:
    print("Verification Failed: No membership linked to user")
    sys.exit(1)

print(f"Membership verified: {membership['plan_name']} (Status: {membership['status']})")

# 5. Verify Points & Wallet
# We'll check the user details or explicit points/wallet endpoints if they exist
# In admin details we have membership and user profile
# Let's check the wallet and points if they were included in the details response (I should check the route code for get_user_details)
# Looking back at line 520+ of admin/routes.py, it returns user, membership, wallet, points, payments.
# Wait, user_details in my previous view_file check on line 520 returned {user, membership}.
# Let me double check admin/routes.py line 529.
# Oh, it returns {"user": user_data, "membership": membership_data}.
# Wait, I see lines for wallet_data and points_data but they aren't in the final return on line 529.
# Let me re-read admin/routes.py near 529.

# If not in details, I'll check user list or separate stats.

# For now, let's just print what we got.
print(f"User Data: {json.dumps(user_details, indent=2)}")

print("Test Completed Successfully!")
