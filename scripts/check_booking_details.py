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

# Get the booking we created
booking_id = "174a00e3-6a57-497a-86e3-2b78a1bc181c"
booking_res = requests.get(f"{BASE_URL}/bookings/{booking_id}", headers=headers)

print(f"Booking status: {booking_res.status_code}")
if booking_res.status_code == 200:
    booking = booking_res.json()
    print(f"Booking user_id: {booking['user_id']}")
    print(f"Booking number: {booking['booking_number']}")
    print(f"Admin user_id: {auth_res.json()['user']['id']}")
else:
    print(f"Error: {booking_res.text}")
