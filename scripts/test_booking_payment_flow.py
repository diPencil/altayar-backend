import requests
import json

BASE_URL = "http://localhost:8082/api"

def test_booking_payment_flow():
    """Test the complete booking to payment flow"""
    try:
        print("=== TESTING BOOKING TO PAYMENT FLOW ===\n")

        # 1. Login as admin
        print("1. Logging in as admin...")
        auth_res = requests.post(f"{BASE_URL}/auth/login", json={
            "identifier": "admin@altayar.com",
            "password": "Admin123"
        })
        if auth_res.status_code != 200:
            print(f"❌ Login failed: {auth_res.text}")
            return

        token = auth_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("✅ Admin login successful\n")

        # 2. Get existing bookings count
        print("2. Checking existing bookings and payments...")
        bookings_before = requests.get(f"{BASE_URL}/bookings", headers=headers)
        payments_before = requests.get(f"{BASE_URL}/payments", headers=headers)

        bookings_count_before = len(bookings_before.json()) if bookings_before.status_code == 200 else 0
        payments_count_before = len(payments_before.json().get('items', [])) if payments_before.status_code == 200 else 0

        print(f"   Bookings before: {bookings_count_before}")
        print(f"   Payments before: {payments_count_before}\n")

        # 3. Get a user to create booking for
        print("3. Finding a user to create booking for...")
        users_res = requests.get(f"{BASE_URL}/admin/users?limit=5", headers=headers)
        if users_res.status_code != 200:
            print(f"❌ Could not get users: {users_res.text}")
            return

        users = users_res.json().get('users', [])
        if not users:
            print("❌ No users found")
            return

        # Find a customer user
        customer = None
        for user in users:
            if user.get('role') == 'CUSTOMER':
                customer = user
                break

        if not customer:
            # Use first user if no customer found
            customer = users[0]
            print(f"⚠️  No customer found, using user: {customer.get('email')}")

        customer_id = customer.get('id')
        customer_email = customer.get('email')
        print(f"✅ Will create booking for user: {customer_email} ({customer_id[:8]}...)\n")

        # 4. Create a test booking
        print("4. Creating test booking...")
        booking_data = {
            "user_id": customer_id,
            "booking_type": "CUSTOM",  # Test our enum fix
            "title_en": "Test Custom Booking",
            "title_ar": "حجز مخصص تجريبي",
            "description_en": "Test booking to verify payment creation",
            "description_ar": "حجز تجريبي للتحقق من إنشاء الدفع",
            "start_date": "2026-02-01",
            "end_date": "2026-02-05",
            "total_amount": 100.00,
            "currency": "USD",
            "guest_count": 2,
            "customer_notes": "Test booking for payment integration",
            "internal_notes": "Created by automated test",
            "items": [
                {
                    "item_type": "service",
                    "description_ar": "خدمة مخصصة",
                    "description_en": "Custom Service",
                    "quantity": 1,
                    "unit_price": 100.00
                }
            ]
        }

        create_res = requests.post(f"{BASE_URL}/bookings", headers=headers, json=booking_data)
        print(f"   Create booking status: {create_res.status_code}")

        if create_res.status_code != 201:
            print(f"❌ Booking creation failed: {create_res.text}")
            return

        booking_response = create_res.json()
        booking_id = booking_response.get('id')
        booking_number = booking_response.get('booking_number')
        print(f"✅ Booking created: {booking_number} (ID: {booking_id})\n")

        # 5. Check if booking appears in admin list
        print("5. Verifying booking appears in admin list...")
        bookings_after = requests.get(f"{BASE_URL}/bookings", headers=headers)
        bookings_count_after = len(bookings_after.json()) if bookings_after.status_code == 200 else 0

        if bookings_count_after > bookings_count_before:
            print(f"✅ Admin bookings count increased: {bookings_count_before} → {bookings_count_after}")
        else:
            print(f"❌ Admin bookings count didn't increase: {bookings_count_before} → {bookings_count_after}")

        # 6. Check if payment was created
        print("6. Checking if payment was created...")
        payments_after = requests.get(f"{BASE_URL}/payments", headers=headers)
        payments_count_after = len(payments_after.json().get('items', [])) if payments_after.status_code == 200 else 0

        if payments_count_after > payments_count_before:
            print(f"✅ Payments count increased: {payments_count_before} → {payments_count_after}")

            # Check if payment is linked to booking
            payments_data = payments_after.json().get('items', [])
            booking_payment = None
            for payment in payments_data:
                if payment.get('booking') and payment['booking'].get('id') == booking_id:
                    booking_payment = payment
                    break

            if booking_payment:
                print(f"✅ Payment linked to booking: {booking_payment.get('payment_number')}")
                print(f"   Payment status: {booking_payment.get('status')}")
                print(f"   Payment amount: {booking_payment.get('amount')} {booking_payment.get('currency')}")
            else:
                print("❌ Payment created but not linked to booking")

        else:
            print(f"❌ Payments count didn't increase: {payments_count_before} → {payments_count_after}")

        # 7. Test user access to booking
        print("7. Testing if user can access their booking...")
        try:
            # Try to login as the customer
            customer_auth = requests.post(f"{BASE_URL}/auth/login", json={
                "identifier": customer_email,
                "password": "Customer123"
            })

            if customer_auth.status_code == 200:
                customer_token = customer_auth.json()["access_token"]
                customer_headers = {"Authorization": f"Bearer {customer_token}"}

                # Test /me endpoint
                user_bookings = requests.get(f"{BASE_URL}/bookings/me", headers=customer_headers)
                print(f"   User /me endpoint status: {user_bookings.status_code}")

                if user_bookings.status_code == 200:
                    user_bookings_data = user_bookings.json()
                    user_booking_count = len(user_bookings_data)
                    print(f"   User sees {user_booking_count} bookings")

                    # Check if our booking is in the list
                    booking_found = any(b.get('id') == booking_id for b in user_bookings_data)
                    if booking_found:
                        print("✅ User can see their booking!")
                    else:
                        print("❌ User cannot see their booking - THIS IS THE BUG!")
                else:
                    print(f"❌ User bookings endpoint failed: {user_bookings.text}")
            else:
                print(f"❌ Could not login as customer: {customer_auth.status_code}")
        except Exception as e:
            print(f"❌ Error testing user access: {e}")

        print("\n=== TEST SUMMARY ===")
        print(f"Booking created: {'✅' if create_res.status_code == 201 else '❌'}")
        print(f"Payment created: {'✅' if payments_count_after > payments_count_before else '❌'}")
        print(f"User can access booking: {'❓' if 'user_bookings_data' not in locals() else ('✅' if any(b.get('id') == booking_id for b in user_bookings_data) else '❌')}")

    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_booking_payment_flow()
