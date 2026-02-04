import requests

BASE_URL = "http://localhost:8082/api"

def test_bookings_list():
    try:
        # 1. Login
        auth_res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "admin@altayar.com", "password": "Admin123"})
        if auth_res.status_code != 200:
            print(f"Login failed: {auth_res.text}")
            return

        token = auth_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. List Bookings (Admin)
        print("\n=== ADMIN BOOKINGS ===")
        print(f"Requesting GET {BASE_URL}/bookings")
        res = requests.get(f"{BASE_URL}/bookings", headers=headers)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"SUCCESS: Admin bookings endpoint returned {len(data)} bookings")
            if data:
                for i, booking in enumerate(data[:3]):  # Show first 3
                    print(f"  {i+1}. {booking.get('booking_number')} - User: {booking.get('user_id')} - Type: {booking.get('booking_type')} - Status: {booking.get('status')}")
                if len(data) > 3:
                    print(f"  ... and {len(data) - 3} more")
        else:
            print(f"FAILURE: Admin bookings endpoint returned {res.status_code}: {res.text}")

        # 3. Check /me (User Bookings for admin)
        print("\n=== USER BOOKINGS (/me) ===")
        print(f"Requesting GET {BASE_URL}/bookings/me")
        res_me = requests.get(f"{BASE_URL}/bookings/me", headers=headers)
        print(f"Status Code (/me): {res_me.status_code}")
        if res_me.status_code == 200:
            data_me = res_me.json()
            print(f"SUCCESS: User bookings endpoint returned {len(data_me)} bookings")
            if data_me:
                for i, booking in enumerate(data_me[:3]):  # Show first 3
                    print(f"  {i+1}. {booking.get('booking_number')} - Type: {booking.get('booking_type')} - Status: {booking.get('status')}")
            else:
                print("  No bookings found for this user")
        else:
            print(f"FAILURE: User bookings endpoint returned {res_me.status_code}: {res_me.text}")

        # 4. Check if admin has any bookings with their user_id
        print(f"\nAdmin user ID: {auth_res.json().get('user', {}).get('id', 'unknown')}")
        print(f"Booking user IDs from admin view: {data[0].get('user_id') if data else 'none'}")

        # 5. Test the customer user that has bookings
        target_user_id = "f3fcea90-234d-412b-9ee3-27b23d5b2bd0"  # From booking data
        print(f"\n=== TESTING TARGET USER {target_user_id[:8]}... ===")

        # Try to get user details
        user_detail_res = requests.get(f"{BASE_URL}/admin/users/{target_user_id}", headers=headers)
        if user_detail_res.status_code == 200:
            user_detail = user_detail_res.json()
            user_email = user_detail.get('email')
            user_role = user_detail.get('role')
            print(f"Target user: {user_email} (Role: {user_role})")

            # Try to login as this user
            user_auth = requests.post(f"{BASE_URL}/auth/login", json={"identifier": user_email, "password": "Customer123"})
            if user_auth.status_code == 200:
                user_token = user_auth.json()["access_token"]
                user_headers = {"Authorization": f"Bearer {user_token}"}

                # Test user bookings
                user_bookings = requests.get(f"{BASE_URL}/bookings/me", headers=user_headers)
                print(f"User bookings status: {user_bookings.status_code}")
                if user_bookings.status_code == 200:
                    user_data = user_bookings.json()
                    print(f"User has {len(user_data)} bookings via /me endpoint")
                    if user_data:
                        for i, booking in enumerate(user_data):
                            print(f"  {i+1}. {booking.get('booking_number')} - Type: {booking.get('booking_type')} - Status: {booking.get('status')}")
                    else:
                        print("  No bookings returned - THIS IS THE BUG!")
                else:
                    print(f"User bookings error: {user_bookings.text}")
            else:
                print(f"Could not login as user: {user_auth.status_code} - {user_auth.text}")
        else:
            print(f"Could not get user details: {user_detail_res.status_code}")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_bookings_list()
