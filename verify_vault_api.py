
import requests
import json
import uuid

BASE_URL = "http://localhost:8082/api"
TEST_EMAIL = f"test_vault_{uuid.uuid4().hex[:6]}@example.com"
TEST_PASSWORD = "Password123!"

def print_result(name, success, data=None):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {name}")
    if data:
        print(json.dumps(data, indent=2))
    print("-" * 40)

def main():
    print("🚀 Starting Payment Vault Verifier...")
    
    # 1. Register User
    print(f"👤 Registering test user: {TEST_EMAIL}")
    try:
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "first_name": "Vault",
            "last_name": "Tester",
            "username": TEST_EMAIL.split("@")[0]
        })
        if reg_resp.status_code not in [200, 201]:
            print_result("Registration", False, reg_resp.text)
            return
        
        # 2. Login
        login_resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        login_data = login_resp.json()
        token = login_data.get("access_token")
        
        if not token:
            print_result("Login", False, login_data)
            return
            
        print_result("Login", True)
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Test GET /cards (Should be empty)
        print("💳 Testing GET /cards...")
        cards_resp = requests.get(f"{BASE_URL}/payments/cards", headers=headers)
        if cards_resp.status_code == 200:
            cards = cards_resp.json()
            is_empty = len(cards) == 0
            print_result("Get Cards (Empty)", is_empty, cards)
        else:
            print_result("Get Cards", False, cards_resp.text)
            
        # 4. Test POST /cards/init (Should return URL)
        print("🔗 Testing POST /cards/init...")
        init_resp = requests.post(f"{BASE_URL}/payments/cards/init", headers=headers)
        if init_resp.status_code == 200:
            data = init_resp.json()
            has_url = "url" in data and data["url"].startswith("http")
            print_result("Init Card Tokenization", has_url, data)
        else:
            print_result("Init Card Tokenization", False, init_resp.text)

    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    main()
