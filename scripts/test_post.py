import urllib.request
import json
import urllib.error

BASE_URL = "http://localhost:8082/api"

def test_create_offer():
    print("Testing POST /api/offers ...")
    
    # Minimal payload matching schema
    payload = {
        "title_ar": "عرض تجريبي",
        "title_en": "Test Offer",
        "original_price": 100,
        "offer_type": "PACKAGE",
        "currency": "USD",
        "status": "ACTIVE",
        "target_audience": "ALL"
    }
    
    data = json.dumps(payload).encode('utf-8')
    
    req = urllib.request.Request(f"{BASE_URL}/offers", method="POST")
    req.add_header('Content-Type', 'application/json')
    req.add_header('Origin', 'http://localhost:8081') # Simulate CORS
    
    try:
        with urllib.request.urlopen(req, data=data) as response:
            print(f"✅ Status: {response.status}")
            print(f"✅ Response: {response.read().decode('utf-8')[:100]}...")
            return True
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP Error: {e.code} {e.reason}")
        print(e.read().decode('utf-8'))
        return False
    except urllib.error.URLError as e:
        print(f"❌ Connection Error: {e.reason}")
        return False

print("=== Verifying POST Offer Creation ===")
test_create_offer()
