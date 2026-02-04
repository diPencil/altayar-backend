"""
Test Fawaterk Payment Creation
Run this to verify the API keys are working
"""
import requests
import json

# Fawaterk credentials
API_KEY = "a9bd550ecbd78778ce88dc8f0928e7673e117e89c0acf5cf23"
BASE_URL = "https://app.fawaterk.com/api/v2"

def test_create_invoice():
    """Test creating a payment invoice"""
    
    url = f"{BASE_URL}/invoiceInitPay"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "payment_method_id": 2,  # 2 = Fawry (usually enabled by default)
        "cartTotal": "100.00",
        "currency": "EGP",
        "customer": {
            "first_name": "محمود",
            "last_name": "أحمد",
            "email": "test@example.com",
            "phone": "01234567890",
            "address": "Cairo, Egypt"
        },
        "redirectionUrls": {
            "successUrl": "http://localhost:8082/payment/success",
            "failUrl": "http://localhost:8082/payment/fail",
            "pendingUrl": "http://localhost:8082/payment/pending"
        },
        "cartItems": [{
            "name": "اختبار دفع",
            "price": "100.00",
            "quantity": 1
        }]
    }
    
    print("=" * 60)
    print("🔵 Testing Fawaterk Invoice Creation")
    print("=" * 60)
    print(f"\nURL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    print("\nSending request...")
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            data = response.json().get('data', {})
            print("\n" + "=" * 60)
            print("✅ SUCCESS!")
            print("=" * 60)
            print(f"Invoice ID: {data.get('invoice_id')}")
            print(f"Invoice Key: {data.get('invoice_key')}")
            print(f"Payment URL: {data.get('url')}")
            print(f"Fawry Code: {data.get('fawry_code', 'N/A')}")
            print("\n🎉 Fawaterk integration is working!")
            return True
        else:
            print("\n" + "=" * 60)
            print("❌ FAILED!")
            print("=" * 60)
            print(f"Error: {response.text}")
            return False
    
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ ERROR!")
        print("=" * 60)
        print(f"Exception: {str(e)}")
        return False

if __name__ == "__main__":
    test_create_invoice()
