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

# Test the /me endpoint for the user we created the booking for
user_id = '7595f034-37ff-4141-bb89-4b1c465b2d26'  # From the test output
user_bookings_res = requests.get(f"{BASE_URL}/bookings/me", headers=headers)

print(f"User bookings status: {user_bookings_res.status_code}")
if user_bookings_res.status_code == 200:
    bookings = user_bookings_res.json()
    print(f"User has {len(bookings)} bookings")
    if bookings:
        booking = bookings[0]
        print(f"Booking: {booking['booking_number']} - User: {booking['user_id']}")
        print(f"Type: {booking['booking_type']} - Status: {booking['status']}")
else:
    print(f"Error: {user_bookings_res.text}")
