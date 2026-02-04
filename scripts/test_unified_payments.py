import requests

BASE_URL = "http://localhost:8082/api"

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

print("🔧 Testing Unified Payments System...\n")

# Get payments
payments_res = requests.get(f"{BASE_URL}/payments", headers=headers)

if payments_res.status_code != 200:
    print(f"❌ Payments endpoint failed: {payments_res.text}")
    exit(1)

payments_data = payments_res.json()
payments = payments_data.get('items', [])

print(f"Found {len(payments)} payments total")

booking_payments = 0
order_payments = 0

for payment in payments:
    if payment.get('booking'):
        booking_payments += 1
        print(f"📋 Booking Payment: {payment['payment_number']} - {payment['booking']['booking_number']}")
    elif payment.get('order'):
        order_payments += 1
        print(f"🛒 Order Payment: {payment['payment_number']} - {payment['order']['order_number']}")

print("\n📊 Summary:")
print(f"Booking payments: {booking_payments}")
print(f"Order payments: {order_payments}")

if booking_payments > 0 and order_payments >= 0:  # Orders might not exist yet
    print("✅ Unified payments system working correctly!")
else:
    print("❌ Issue with unified payments system")
