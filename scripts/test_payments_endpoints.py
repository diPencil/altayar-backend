import requests

BASE_URL = "http://localhost:8082/api"

def test_payments_endpoints():
    try:
        # 1. Login
        auth_res = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "admin@altayar.com", "password": "Admin123"})
        if auth_res.status_code != 200:
            print(f"Login failed: {auth_res.text}")
            return

        token = auth_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test GET /api/payments (admin)
        print(f"Requesting GET {BASE_URL}/payments")
        res = requests.get(f"{BASE_URL}/payments", headers=headers)
        print(f"Status Code: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            print(f"SUCCESS: Admin payments endpoint returned {len(data.get('items', []))} items")
        else:
            print(f"FAILURE: Admin payments endpoint returned {res.status_code}: {res.text}")

        # 3. Test GET /api/payments/my-payments (user)
        print(f"Requesting GET {BASE_URL}/payments/my-payments")
        res_my = requests.get(f"{BASE_URL}/payments/my-payments", headers=headers)
        print(f"Status Code (/my-payments): {res_my.status_code}")
        if res_my.status_code == 200:
            data = res_my.json()
            print(f"SUCCESS: User payments endpoint returned {len(data.get('items', []))} items")
        else:
            print(f"FAILURE: User payments endpoint returned {res_my.status_code}: {res_my.text}")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_payments_endpoints()
