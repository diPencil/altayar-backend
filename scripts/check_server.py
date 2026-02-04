

import requests
import sys

BASE_URL = "http://localhost:8082"

def check_health():
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        print(f"Health Check: {response.status_code}")
    except Exception as e:
        print(f"Health Check Failed: {e}")
        sys.exit(1)

def test_login():
    try:
        # FastAPI OAuth2PasswordRequestForm expects form-urlencoded data
        # requests.post default 'data' argument does exactly this.
        # But let's be explicit and concise.
        payload = {
            "username": "admin@altayar.com", 
            "password": "admin123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", data=payload)
        
        print(f"Login Status: {response.status_code}")
        if response.status_code == 200:
            print("Login Successful!")
            print(response.json().keys())
        else:
            print(f"Login Failed: {response.text}")
    except Exception as e:
        print(f"Login Exception: {e}")

if __name__ == "__main__":
    check_health()
    test_login()

