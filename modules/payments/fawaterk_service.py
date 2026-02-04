import requests
import hashlib
import hmac
import json
from typing import Dict, Any, Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class FawaterkService:
    """
    Fawaterk Payment Gateway Integration
    Official API: https://app.fawaterk.com/api/v2
    """
    
    def __init__(self):
        self.api_key = settings.FAWATERK_API_KEY
        self.vendor_key = settings.FAWATERK_VENDOR_KEY
        self.base_url = settings.FAWATERK_BASE_URL
        self.test_mode = settings.FAWATERK_TEST_MODE
    
    def create_invoice(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create payment invoice on Fawaterk
        Returns: {'invoice_id', 'invoice_key', 'url', 'fawry_code', etc.}
        """
        url = f"{self.base_url}/invoiceInitPay"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Fawaterk expected payload structure
        payload = {
            "payment_method_id": payment_data.get("payment_method_id", 1),  # 1=card, 2=fawry, etc.
            "cartTotal": str(payment_data["amount"]),
            "currency": payment_data.get("currency", settings.DEFAULT_CURRENCY),  # Use setting as fallback
            "customer": {
                "first_name": payment_data["customer_first_name"],
                "last_name": payment_data.get("customer_last_name", ""),
                "email": payment_data["customer_email"],
                "phone": payment_data.get("customer_phone", ""),
                "address": payment_data.get("customer_address", "")
            },
            "redirectionUrls": {
                "successUrl": payment_data.get("success_url", settings.PAYMENT_SUCCESS_URL),
                "failUrl": payment_data.get("fail_url", settings.PAYMENT_FAIL_URL),
                "pendingUrl": payment_data.get("fail_url", settings.PAYMENT_FAIL_URL)
            },
            "cartItems": payment_data.get("cart_items", [{
                "name": payment_data.get("description", "Payment"),
                "price": str(payment_data["amount"]),
                "quantity": 1
            }])
        }

        # If save_card is requested, add it to the payload
        if payment_data.get("save_card"):
            payload["save_card"] = True
            # For Fawaterk v2, saving card often requires a specific tokenization flow or flag
            # We add it here to ensure it's captured if supported by the endpoint
            logger.info("🟢 Card will be tokenized/saved during this transaction")
        
        logger.info(f"🔵 Creating Fawaterk invoice: {payload['cartTotal']} {payload['currency']}")
        logger.info(f"🔵 Fawaterk payload: {json.dumps(payload, indent=2)}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            # Log raw response
            logger.info(f"🔵 Fawaterk response status: {response.status_code}")
            logger.info(f"🔵 Fawaterk response body: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            
            # Check if response has data
            if 'data' not in result:
                logger.error(f"❌ Fawaterk response missing 'data' field: {result}")
                raise Exception(f"Invalid Fawaterk response structure: {result}")
            
            data = result.get('data', {})
            
            # Extract payment URL - Fawaterk returns it in different places
            payment_url = None
            
            # Method 1: Direct 'url' field
            if 'url' in data:
                payment_url = data['url']
            
            # Method 2: Inside payment_data.redirectTo
            elif 'payment_data' in data and isinstance(data['payment_data'], dict):
                payment_url = data['payment_data'].get('redirectTo')
            
            # Method 3: Direct redirectTo field
            elif 'redirectTo' in data:
                payment_url = data['redirectTo']
            
            if not payment_url:
                logger.error(f"❌ Fawaterk response missing payment URL: {data}")
                raise Exception(f"Fawaterk did not return payment URL. Response: {data}")
            
            # Add the URL to the data dict for consistency
            data['url'] = payment_url
            
            logger.info(f"✅ Fawaterk invoice created: {data.get('invoice_id')}")
            logger.info(f"✅ Payment URL: {payment_url}")
            return data
        
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text if e.response else str(e)
            logger.error(f"❌ Fawaterk HTTP error: {error_text}")
            raise Exception(f"Fawaterk API error: {error_text}")
        except Exception as e:
            logger.error(f"❌ Fawaterk error: {str(e)}")
            raise Exception(f"Failed to create Fawaterk invoice: {str(e)}")
    
    def verify_webhook_hash_paid_or_failed(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """
        Verify webhook hash for PAID/FAILED events using HMAC-SHA256.
        
        Per Fawaterk docs:
        queryParam = "InvoiceId=<invoice_id>&InvoiceKey=<invoice_key>&PaymentMethod=<payment_method>"
        hash = HMAC_SHA256(queryParam, FAWATERAK_VENDOR_KEY)
        
        Returns: (is_valid, hash_computed)
        """
        try:
            invoice_id = str(payload.get("invoice_id", payload.get("InvoiceId", "")))
            invoice_key = str(payload.get("invoice_key", payload.get("InvoiceKey", "")))
            payment_method = str(payload.get("payment_method", payload.get("PaymentMethod", "")))
            hash_received = str(payload.get("hashKey", payload.get("signature", "")))
            
            # Build query param string exactly as Fawaterk specifies
            query_param = f"InvoiceId={invoice_id}&InvoiceKey={invoice_key}&PaymentMethod={payment_method}"
            
            # Compute HMAC-SHA256
            hash_computed = hmac.new(
                self.vendor_key.encode('utf-8'),
                query_param.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(hash_received.lower(), hash_computed.lower())
            
            if is_valid:
                logger.info(f"✅ Webhook hash VALID for invoice {invoice_id}")
            else:
                logger.warning(f"⚠️  Webhook hash INVALID for invoice {invoice_id}")
                logger.debug(f"Query: {query_param}")
                logger.debug(f"Expected: {hash_computed}, Received: {hash_received}")
            
            return is_valid, hash_computed
        
        except Exception as e:
            logger.error(f"❌ Error verifying webhook hash: {str(e)}")
            return False, ""
    
    def verify_webhook_hash_expired(self, payload: Dict[str, Any]) -> tuple[bool, str]:
        """
        Verify webhook hash for EXPIRED events (Fawry/Aman/Masary) using HMAC-SHA256.
        
        Per Fawaterk docs:
        queryParam = "referenceId=<referenceId>&PaymentMethod=<paymentMethod>"
        hash = HMAC_SHA256(queryParam, FAWATERAK_VENDOR_KEY)
        
        Returns: (is_valid, hash_computed)
        """
        try:
            reference_id = str(payload.get("referenceId", payload.get("reference_id", "")))
            payment_method = str(payload.get("paymentMethod", payload.get("PaymentMethod", payload.get("payment_method", ""))))
            hash_received = str(payload.get("hashKey", payload.get("signature", "")))
            
            # Build query param string exactly as Fawaterk specifies
            query_param = f"referenceId={reference_id}&PaymentMethod={payment_method}"
            
            # Compute HMAC-SHA256
            hash_computed = hmac.new(
                self.vendor_key.encode('utf-8'),
                query_param.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            is_valid = hmac.compare_digest(hash_received.lower(), hash_computed.lower())
            
            if is_valid:
                logger.info(f"✅ Expired webhook hash VALID for reference {reference_id}")
            else:
                logger.warning(f"⚠️  Expired webhook hash INVALID for reference {reference_id}")
                logger.debug(f"Query: {query_param}")
                logger.debug(f"Expected: {hash_computed}, Received: {hash_received}")
            
            return is_valid, hash_computed
        
        except Exception as e:
            logger.error(f"❌ Error verifying expired webhook hash: {str(e)}")
            return False, ""
    
    def check_payment_status(self, invoice_id: str) -> Dict[str, Any]:
        """
        Query payment status from Fawaterk
        """
        url = f"{self.base_url}/getInvoiceData/{invoice_id}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get('data', {})
        
        except Exception as e:
            logger.error(f"❌ Error checking payment status: {str(e)}")
            raise Exception(f"Failed to check payment status: {str(e)}")

    def create_card_token_url(self, user_data: Dict[str, Any], redirect_url: str) -> str:
        """
        Generate URL for user to enter card details for tokenization.
        Endpoint: /api/v2/invoice/createCardTokenScreen (or similar)
        Ref: https://fawaterk.com/api/v2
        """
        # Using the standard invoice initialization but with 'tokenization' flag if supported,
        # OR use the specific endpoint found in docs.
        # Based on search results: createCardTokenScreen
        
        url = f"{self.base_url}/createCardTokenScreen"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "customer": {
                "first_name": user_data['first_name'],
                "last_name": user_data['last_name'],
                "email": user_data['email'],
                "phone": user_data['phone'],
                "address": "Cairo, Egypt" # Required by some gateways
            },
            "redirectionUrls": {
                "successUrl": redirect_url,
                "failUrl": redirect_url, # Frontend handles status
            },
            "customer_unique_id": str(user_data['id']) # Crucial for linking
        }
        
        logger.info(f"🔵 Creating Card Token Screen for user {user_data['id']}")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            result = response.json()
            
            if 'data' not in result or 'url' not in result['data']:
                raise Exception(f"Invalid response from Fawaterk: {result}")
                
            return result['data']['url']
            
        except Exception as e:
            logger.error(f"❌ Failed to get tokenization URL: {str(e)}")
            raise Exception(f"Tokenization initialization failed: {str(e)}")