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
        # Test mode: use staging URL if base is production (test keys often only work on staging)
        base = settings.FAWATERK_BASE_URL
        if getattr(settings, "FAWATERK_TEST_MODE", False) and "app.fawaterk.com" in base:
            base = "https://staging.fawaterk.com/api/v2"
            logger.info(f"🔵 Fawaterk TEST_MODE: using staging URL {base}")
        self.base_url = base
        self.test_mode = getattr(settings, "FAWATERK_TEST_MODE", True)
    
    def _build_payload(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build Fawaterk payload (shared for create_invoice and raw call)."""
        success_url = payment_data.get("success_url") or settings.PAYMENT_SUCCESS_URL
        fail_url = payment_data.get("fail_url") or settings.PAYMENT_FAIL_URL
        base = (getattr(settings, "APP_BASE_URL", "") or getattr(settings, "PAYMENT_REDIRECT_BASE_URL", "") or "").strip()
        if success_url.startswith("altayarvip://") and base.lower().startswith("https://"):
            base = base.rstrip("/")
            success_url = f"{base}/api/payments/success"
            fail_url = f"{base}/api/payments/fail"
            logger.info(f"🔵 Using derived payment redirect URLs: success={success_url}, fail={fail_url}")
        customer_phone = payment_data.get("customer_phone") or ""
        if not customer_phone.strip():
            customer_phone = "0000000000"
        customer_address = payment_data.get("customer_address") or ""
        if not customer_address.strip():
            customer_address = "N/A"
        currency = payment_data.get("currency") or settings.DEFAULT_CURRENCY
        if getattr(settings, "FAWATERK_FORCE_CURRENCY", None):
            currency = settings.FAWATERK_FORCE_CURRENCY
        payment_method_id = payment_data.get("payment_method_id")
        if payment_method_id is None:
            payment_method_id = getattr(settings, "FAWATERK_DEFAULT_PAYMENT_METHOD", 2)
        if currency and str(currency).upper() == "USD":
            payment_method_id = 1
        elif currency and str(currency).upper() == "EGP":
            payment_method_id = 2
        amount = float(payment_data["amount"])
        cart_items = payment_data.get("cart_items")
        if not cart_items:
            cart_items = [{"name": payment_data.get("description", "Payment"), "price": amount, "quantity": 1}]
        # Fawaterk may expect string or number for cartTotal/price - try string first (API doc shows strings)
        payload = {
            "payment_method_id": payment_method_id,
            "cartTotal": str(amount),
            "currency": currency,
            "customer": {
                "first_name": payment_data.get("customer_first_name") or "Customer",
                "last_name": payment_data.get("customer_last_name") or "",
                "email": payment_data.get("customer_email") or "customer@example.com",
                "phone": customer_phone,
                "address": customer_address
            },
            "redirectionUrls": {"successUrl": success_url, "failUrl": fail_url, "pendingUrl": fail_url},
            "cartItems": [{"name": str(i.get("name", "Item")), "price": str(i.get("price", amount)), "quantity": int(i.get("quantity", 1))} for i in cart_items]
        }
        if payment_data.get("save_card"):
            payload["save_card"] = True
        return payload
    
    def _do_request(self, payload: Dict[str, Any]) -> requests.Response:
        url = f"{self.base_url}/invoiceInitPay"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        return requests.post(url, json=payload, headers=headers, timeout=30)
    
    def create_invoice(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create payment invoice on Fawaterk.
        On 422, retries once with the other payment method (Card vs Fawry).
        Returns: {'invoice_id', 'invoice_key', 'url', 'fawry_code', etc.}
        """
        payload = self._build_payload(payment_data)
        logger.info(f"🔵 Fawaterk payload: {json.dumps(payload, indent=2)}")
        
        def parse_error(response: requests.Response) -> str:
            body = response.text
            try:
                err_json = response.json()
                msg = (
                    err_json.get("message") or err_json.get("msg") or err_json.get("error")
                    or (err_json.get("detail") if isinstance(err_json.get("detail"), str) else None)
                )
                if not msg and isinstance(err_json.get("detail"), list):
                    parts = [str(d.get("msg", d)) for d in err_json["detail"] if isinstance(d, dict)]
                    if parts:
                        msg = "; ".join(parts[:5])
                if not msg and err_json.get("errors"):
                    msg = str(err_json["errors"])[:300]
                if msg:
                    return msg
            except (ValueError, TypeError, KeyError):
                pass
            return body[:400] if len(body) > 400 else body
        
        def handle_response(response: requests.Response) -> Dict[str, Any]:
            logger.info(f"🔵 Fawaterk response status: {response.status_code}, body: {response.text[:500]}")
            if not response.ok:
                logger.error(f"❌ Fawaterk HTTP {response.status_code}: {response.text}")
                err_msg = parse_error(response)
                raise Exception(f"Fawaterk: {err_msg}. (تأكد من إضافة دومين الـ redirect في لوحة Fawaterk: Integrations)")
            result = response.json()
            if "data" not in result:
                raise Exception(f"Invalid Fawaterk response: {result}")
            data = result.get("data", {})
            payment_url = data.get("url") or (data.get("payment_data") or {}).get("redirectTo") or data.get("redirectTo")
            if not payment_url:
                raise Exception(f"Fawaterk did not return payment URL: {data}")
            data["url"] = payment_url
            logger.info(f"✅ Fawaterk invoice created: {data.get('invoice_id')}")
            return data
        
        try:
            response = self._do_request(payload)
            if response.ok:
                return handle_response(response)
            if response.status_code == 422:
                # Retry with the other payment method (Card<->Fawry)
                other = 2 if payload["payment_method_id"] == 1 else 1
                logger.info(f"🔵 Fawaterk 422, retrying with payment_method_id={other}")
                payload["payment_method_id"] = other
                response2 = self._do_request(payload)
                if response2.ok:
                    return handle_response(response2)
                err_msg = parse_error(response2)
                raise Exception(f"Fawaterk: {err_msg}. (أضف دومين الـ redirect في لوحة Fawaterk: Integrations)")
            err_msg = parse_error(response)
            raise Exception(f"Fawaterk: {err_msg}")
        except Exception as e:
            if "Fawaterk:" in str(e):
                raise
            logger.error(f"❌ Fawaterk error: {str(e)}")
            raise Exception(f"Failed to create Fawaterk invoice: {str(e)}")
    
    def debug_invoice_request(self, amount: float = 100, currency: str = "USD") -> Dict[str, Any]:
        """Call Fawaterk with minimal payload and return raw response (for debugging 422)."""
        payment_data = {
            "amount": amount,
            "currency": currency,
            "customer_first_name": "Test",
            "customer_last_name": "User",
            "customer_email": "test@example.com",
            "customer_phone": "01234567890",
            "description": "Debug test",
        }
        payload = self._build_payload(payment_data)
        response = self._do_request(payload)
        return {
            "status_code": response.status_code,
            "response_text": response.text,
            "request_payload": payload,
            "base_url": self.base_url,
        }
    
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