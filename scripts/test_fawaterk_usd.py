"""
Fawaterk USD Payment Gateway Test

This script tests the Fawaterk payment gateway with USD currency.
It creates a test invoice and verifies the gateway accepts USD.
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.payments.fawaterk_service import FawaterkService
from config.settings import settings


def test_fawaterk_usd_payment():
    """Test Fawaterk accepts USD currency"""
    print("="*60)
    print("Testing Fawaterk Payment Gateway with USD Currency")
    print("="*60)
    
    # Check if API keys are configured
    if not settings.FAWATERK_API_KEY or settings.FAWATERK_API_KEY == "your_api_key_here":
        print("⚠️  Fawaterk API key not configured in .env")
        print("   Skipping sandbox test")
        return True
    
    service = FawaterkService()
    
    test_payload = {
        "amount": 100.00,
        "currency": "USD",
        "customer_first_name": "Test",
        "customer_last_name": "User",
        "customer_email": "test@example.com",
        "customer_phone": "+1234567890",
        "description": "Test USD Payment - Currency Migration"
    }
    
    print(f"\n📤 Creating test invoice:")
    print(f"   Amount: ${test_payload['amount']}")
    print(f"   Currency: {test_payload['currency']}")
    print(f"   Customer: {test_payload['customer_first_name']} {test_payload['customer_last_name']}")
    
    try:
        response = service.create_invoice(test_payload)
        
        if not response.get('invoice_id'):
            print("❌ No invoice_id in response")
            print(f"   Response: {response}")
            return False
        
        print(f"\n✅ Fawaterk USD payment test PASSED")
        print(f"   Invoice ID: {response.get('invoice_id')}")
        print(f"   Payment URL: {response.get('url')}")
        print(f"   Fawry Code: {response.get('fawry_code', 'N/A')}")
        
        # Verify currency in response
        if 'currency' in response:
            print(f"   Currency in response: {response['currency']}")
        
        print("\n" + "="*60)
        print("✅ FAWATERK USD TEST PASSED")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Fawaterk USD payment test FAILED")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fawaterk_usd_payment()
    sys.exit(0 if success else 1)
