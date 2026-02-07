from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import logging
import time

from modules.payments.models import Payment, PaymentWebhookLog, PaymentType, PaymentStatus, PaymentProvider, PaymentMethod
from modules.payments.fawaterk_service import FawaterkService
from modules.orders.models import Order, OrderItem, OrderStatus, PaymentStatus as OrderPaymentStatus
from modules.bookings.models import Booking, BookingStatus, PaymentStatus as BookingPaymentStatus
from shared.utils import generate_unique_number
from shared.exceptions import PaymentException, NotFoundException
from config.settings import settings

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.fawaterk = FawaterkService()
    
    def initiate_order_payment(
        self,
        order_id: str,
        user_id: str,
        payment_method_id: int = 1,  # 1=card, 2=fawry
        success_url: Optional[str] = None,
        fail_url: Optional[str] = None,
        save_card: bool = False
    ) -> Dict[str, Any]:
        """
        Initiate payment for an order via Fawaterk.
        
        Returns:
            - payment_url: URL to open in mobile WebView
            - payment_id: Internal payment ID
            - status: PENDING
        """
        # Get order
        order = self.db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == user_id
        ).first()
        
        if not order:
            raise NotFoundException("Order not found")
        
        if order.payment_status == OrderPaymentStatus.PAID:
            raise PaymentException("Order already paid")
        
        # Get user - for MVP we'll use minimal data
        from modules.users.models import User
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # For MVP/testing, allow orders without full user data
        customer_first_name = user.first_name if user else "Customer"
        customer_last_name = user.last_name if user else "User"
        customer_email = user.email if user else f"customer-{user_id[:8]}@test.com"
        customer_phone = user.phone if user else ""
        
        # Generate payment number
        sequence = self.db.query(Payment).count() + 1
        payment_number = generate_unique_number("PAY", sequence)
        
        # Generate idempotency key
        idempotency_key = str(uuid4())
        
        # Create payment record
        payment = Payment(
            id=str(uuid4()),
            payment_number=payment_number,
            user_id=user_id,
            order_id=order_id,
            payment_type=PaymentType.ORDER,
            amount=order.total_amount,
            currency=order.currency or settings.DEFAULT_CURRENCY,
            provider=PaymentProvider.FAWATERK,
            status=PaymentStatus.PENDING,
            idempotency_key=idempotency_key
        )
        
        self.db.add(payment)
        self.db.commit()
        self.db.refresh(payment)
        
        # Prepare Fawaterk payload
        try:
            fawaterk_data = {
                "payment_method_id": payment_method_id,
                "amount": float(order.total_amount),
                "currency": order.currency or settings.DEFAULT_CURRENCY,
                "customer_first_name": customer_first_name,
                "customer_last_name": customer_last_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_address": "",
                "success_url": success_url or settings.PAYMENT_SUCCESS_URL,
                "fail_url": fail_url or settings.PAYMENT_FAIL_URL,
                "description": f"Order {order.order_number}",
                "save_card": save_card,
                "cart_items": [{
                    "name": f"Order {order.order_number}",
                    "price": str(order.total_amount),
                    "quantity": 1
                }]
            }
            
            # Create Fawaterk invoice
            invoice_response = self.fawaterk.create_invoice(fawaterk_data)
            
            # Update payment with Fawaterk details
            payment.provider_transaction_id = str(invoice_response.get("invoice_id", ""))
            payment.provider_invoice_id = str(invoice_response.get("invoice_id", ""))
            payment.provider_reference_id = invoice_response.get("invoice_key", "")
            payment.payment_details = invoice_response
            
            self.db.commit()
            self.db.refresh(payment)
            
            logger.info(f"✅ Payment initiated: {payment_number} for order {order.order_number}")
            
            return {
                "payment_id": str(payment.id),
                "payment_number": payment_number,
                "order_number": order.order_number,
                "amount": float(order.total_amount),
                "currency": order.currency,
                "status": "PENDING",
                "invoice_id": str(invoice_response.get("invoice_id", "")),
                "invoice_key": invoice_response.get("invoice_key", ""),
                "payment_url": invoice_response.get("url", ""),
                "fawry_code": invoice_response.get("fawry_code"),
                "qr_code_url": invoice_response.get("qr_code"),
                "expires_at": invoice_response.get("expire_date")
            }
        
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            self.db.commit()
            raise PaymentException(f"Failed to initiate payment: {str(e)}")

    def initiate_booking_payment(
        self,
        booking_id: str,
        user_id: str,
        payment_method_id: int = 1,  # 1=card, 2=fawry
        success_url: Optional[str] = None,
        fail_url: Optional[str] = None,
        save_card: bool = False
    ) -> Dict[str, Any]:
        """
        Initiate payment for a booking via Fawaterk.
        
        Returns:
            - payment_url: URL to open in mobile WebView
            - payment_id: Internal payment ID
            - status: PENDING
        """
        # Get booking
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.user_id == user_id
        ).first()
        
        if not booking:
            raise NotFoundException("Booking not found")
        
        if booking.payment_status == BookingPaymentStatus.PAID:
            raise PaymentException("Booking already paid")
        
        # Get user
        from modules.users.models import User
        user = self.db.query(User).filter(User.id == user_id).first()
        
        customer_first_name = user.first_name if user else "Customer"
        customer_last_name = user.last_name if user else "User"
        customer_email = user.email if user else f"customer-{user_id[:8]}@test.com"
        customer_phone = user.phone if user else ""
        
        # Check if payment record exists (created by admin manual booking or previous attempt)
        payment = self.db.query(Payment).filter(
            Payment.booking_id == booking_id,
            Payment.status == PaymentStatus.PENDING
        ).first()
        
        if not payment:
            # Create new payment record if not exists
            # Use helper from bookings module if possible, or create here directly
            # To avoid circular imports, we'll create here similar to order payment
            
            sequence = self.db.query(Payment).count() + 1
            payment_number = generate_unique_number("PAY", sequence)
            idempotency_key = str(uuid4())
            
            payment = Payment(
                id=str(uuid4()),
                payment_number=payment_number,
                user_id=user_id,
                booking_id=booking_id,
                payment_type=PaymentType.BOOKING,
                amount=booking.total_amount,
                currency=booking.currency or settings.DEFAULT_CURRENCY,
                provider=PaymentProvider.FAWATERK,
                status=PaymentStatus.PENDING,
                idempotency_key=idempotency_key,
                payment_details={
                    "booking_number": booking.booking_number,
                    "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
                    "title_en": booking.title_en,
                    "title_ar": booking.title_ar
                }
            )
            self.db.add(payment)
            self.db.commit()
            self.db.refresh(payment)
        else:
            # Update existing pending payment
            # Ensure amount matches booking (in case booking changed)
            if float(payment.amount) != float(booking.total_amount):
                payment.amount = booking.total_amount
                
            payment.provider = PaymentProvider.FAWATERK
            payment.idempotency_key = str(uuid4()) # New attempt
            self.db.commit()
            self.db.refresh(payment)
            
        payment_number = payment.payment_number
        
        # Prepare Fawaterk payload
        try:
            fawaterk_data = {
                "payment_method_id": payment_method_id,
                "amount": float(booking.total_amount),
                "currency": booking.currency or settings.DEFAULT_CURRENCY,
                "customer_first_name": customer_first_name,
                "customer_last_name": customer_last_name,
                "customer_email": customer_email,
                "customer_phone": customer_phone,
                "customer_address": "",
                "success_url": success_url or settings.PAYMENT_SUCCESS_URL,
                "fail_url": fail_url or settings.PAYMENT_FAIL_URL,
                "description": f"Booking {booking.booking_number}",
                "save_card": save_card,
                "cart_items": [{
                    "name": f"Booking {booking.booking_number}",
                    "price": str(booking.total_amount),
                    "quantity": 1
                }]
            }
            
            # Create Fawaterk invoice
            invoice_response = self.fawaterk.create_invoice(fawaterk_data)
            
            # Update payment with Fawaterk details
            payment.provider_transaction_id = str(invoice_response.get("invoice_id", ""))
            payment.provider_invoice_id = str(invoice_response.get("invoice_id", ""))
            payment.provider_reference_id = invoice_response.get("invoice_key", "")
            payment.payment_details = invoice_response
            
            self.db.commit()
            self.db.refresh(payment)
            
            logger.info(f"✅ Payment initiated: {payment_number} for booking {booking.booking_number}")
            
            return {
                "payment_id": str(payment.id),
                "payment_number": payment_number,
                "booking_number": booking.booking_number,
                "amount": float(booking.total_amount),
                "currency": booking.currency,
                "status": "PENDING",
                "invoice_id": str(invoice_response.get("invoice_id", "")),
                "invoice_key": invoice_response.get("invoice_key", ""),
                "payment_url": invoice_response.get("url", ""),
                "fawry_code": invoice_response.get("fawry_code"),
                "qr_code_url": invoice_response.get("qr_code"),
                "expires_at": invoice_response.get("expire_date")
            }
        
        except Exception as e:
            payment.status = PaymentStatus.FAILED
            payment.error_message = str(e)
            self.db.commit()
            raise PaymentException(f"Failed to initiate payment: {str(e)}")
    
    def handle_fawaterk_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle Fawaterk webhook with idempotency.
        
        Supports 3 cases:
        1. invoice_status = paid
        2. failed payment
        3. expired (Fawry/Aman/Masary)
        
        Hash Verification (per Fawaterk docs):
        - PAID/FAILED: HMAC_SHA256("InvoiceId=X&InvoiceKey=Y&PaymentMethod=Z", VENDOR_KEY)
        - EXPIRED: HMAC_SHA256("referenceId=X&PaymentMethod=Y", VENDOR_KEY)
        
        Idempotency:
        - Uses invoice_id + invoice_key uniqueness
        - Stores all webhook events in payment_webhook_logs
        - Ignores duplicate events
        """
        start_time = time.time()
        
        # Check for card tokenization event
        if payload.get("token") or payload.get("card_token"):
             self.process_token_webhook(payload)
             return {"status": "success", "message": "Token processed"}
        
        # Extract webhook data - handle both camelCase and snake_case
        invoice_id = str(payload.get("invoice_id", payload.get("InvoiceId", "")))
        invoice_key = str(payload.get("invoice_key", payload.get("InvoiceKey", "")))
        invoice_status = str(payload.get("invoice_status", payload.get("InvoiceStatus", ""))).upper()
        reference_id = str(payload.get("referenceId", payload.get("reference_id", "")))
        payment_method = str(payload.get("payment_method", payload.get("PaymentMethod", "")))
        hash_received = str(payload.get("hashKey", payload.get("signature", "")))
        
        # Determine event type
        if invoice_status == "PAID":
            event_type = "PAID"
        elif invoice_status in ["FAILED", "CANCEL", "CANCELLED"]:
            event_type = "FAILED"
        elif invoice_status in ["EXPIRED", "EXPIRE"]:
            event_type = "EXPIRED"
        else:
            event_type = "UNKNOWN"
        
        logger.info(f"🔵 Webhook received: invoice={invoice_id}, key={invoice_key}, status={invoice_status}, event={event_type}")
        
        # Check idempotency: have we processed this exact webhook before?
        # Use invoice_id + invoice_key + event_type for uniqueness
        existing_log = self.db.query(PaymentWebhookLog).filter(
            PaymentWebhookLog.provider == "FAWATERK",
            PaymentWebhookLog.invoice_id == invoice_id,
            PaymentWebhookLog.invoice_key == invoice_key,
            PaymentWebhookLog.event_type == event_type,
            PaymentWebhookLog.processed == True
        ).first()
        
        if existing_log:
            logger.warning(f"⚠️  Webhook already processed: invoice={invoice_id}, key={invoice_key}, event={event_type}")
            return {"status": "already_processed", "message": "Webhook already processed"}
        
        # Verify hash using correct HMAC-SHA256 method
        if event_type == "EXPIRED":
            is_valid, hash_computed = self.fawaterk.verify_webhook_hash_expired(payload)
        else:
            # PAID and FAILED use the same verification method
            is_valid, hash_computed = self.fawaterk.verify_webhook_hash_paid_or_failed(payload)
        
        # Find payment by invoice_id
        payment = self.db.query(Payment).filter(
            Payment.provider_invoice_id == invoice_id
        ).first()
        
        # Create webhook log
        webhook_log = PaymentWebhookLog(
            id=str(uuid4()),
            provider="FAWATERK",
            event_type=event_type,
            invoice_id=invoice_id,
            invoice_key=invoice_key,
            reference_id=reference_id,
            raw_payload=payload,
            hash_received=hash_received,
            hash_computed=hash_computed,
            is_valid=is_valid,
            payment_id=str(payment.id) if payment else None,
            processed=False
        )
        
        self.db.add(webhook_log)
        self.db.commit()
        
        if not is_valid:
            webhook_log.error_message = "Invalid hash signature (HMAC-SHA256 verification failed)"
            self.db.commit()
            logger.error(f"❌ Invalid webhook hash for invoice {invoice_id}")
            raise PaymentException("Invalid webhook signature")
        
        if not payment:
            webhook_log.error_message = f"Payment not found for invoice {invoice_id}"
            self.db.commit()
            logger.error(f"❌ Payment not found for invoice {invoice_id}")
            raise NotFoundException(f"Payment not found for invoice {invoice_id}")
        
        try:
            # Process based on event type
            if event_type == "PAID":
                if payment.status == PaymentStatus.PAID:
                    logger.warning(f"⚠️  Payment already marked as PAID: {payment.payment_number}")
                    webhook_log.processed = True
                    webhook_log.processed_at = datetime.utcnow()
                    self.db.commit()
                    return {"status": "already_paid", "message": "Payment already marked as paid"}
                
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.utcnow()
                payment.payment_method = self._map_payment_method(payment_method)
                payment.webhook_payload = payload
                payment.webhook_received_at = datetime.utcnow()
                payment.webhook_event_id = f"{invoice_id}:{invoice_key}"
                
                # Update order
                if payment.order_id:
                    order = self.db.query(Order).filter(Order.id == payment.order_id).first()
                    if order:
                        order.payment_status = OrderPaymentStatus.PAID
                        if order.status == OrderStatus.ISSUED:
                            order.status = OrderStatus.PAID
                        order.paid_at = datetime.utcnow()
                        order.paid_at = datetime.utcnow()
                        logger.info(f"✅ Order {order.order_number} marked as PAID")

                        # Check if this order is linked to a Booking
                        for item in order.items:
                            if item.item_metadata and item.item_metadata.get('booking_id'):
                                booking_id = item.item_metadata.get('booking_id')
                                booking = self.db.query(Booking).filter(Booking.id == booking_id).first()
                                if booking:
                                    # Update Booking Status
                                    booking.payment_status = BookingPaymentStatus.PAID
                                    booking.status = BookingStatus.CONFIRMED
                                    booking.confirmed_at = datetime.utcnow()
                                    self.db.commit() # Commit inner change
                                    logger.info(f"✅ Linked Booking {booking.booking_number} auto-confirmed via Invoice Payment")
                
                logger.info(f"✅ Payment {payment.payment_number} marked as PAID")
            
            elif event_type == "FAILED":
                payment.status = PaymentStatus.FAILED
                payment.failed_at = datetime.utcnow()
                payment.error_message = payload.get("failure_reason", payload.get("failureReason", "Payment failed"))
                payment.webhook_payload = payload
                payment.webhook_received_at = datetime.utcnow()
                logger.info(f"❌ Payment {payment.payment_number} marked as FAILED")
            
            elif event_type == "EXPIRED":
                payment.status = PaymentStatus.EXPIRED
                payment.expired_at = datetime.utcnow()
                payment.webhook_payload = payload
                payment.webhook_received_at = datetime.utcnow()
                logger.info(f"⏱️  Payment {payment.payment_number} marked as EXPIRED")
            
            # Mark webhook as processed
            webhook_log.processed = True
            webhook_log.processed_at = datetime.utcnow()
            webhook_log.processing_time_ms = int((time.time() - start_time) * 1000)
            
            self.db.commit()
            
            logger.info(f"✅ Webhook processed successfully in {webhook_log.processing_time_ms}ms")
            
            return {
                "status": "success",
                "message": "Webhook processed successfully",
                "payment_number": payment.payment_number,
                "payment_status": payment.status.value
            }
        
        except Exception as e:
            webhook_log.error_message = str(e)
            self.db.commit()
            logger.error(f"❌ Error processing webhook: {str(e)}")
            raise

    def _map_payment_method(self, method_str: str) -> Optional[PaymentMethod]:
        """
        Map provider payment method string/id to our PaymentMethod enum.

        Fawaterk often returns either a string (e.g. 'card', 'fawry') or a numeric method id.
        """
        if not method_str:
            return None

        ms = str(method_str).strip().lower()

        method_map = {
            # String labels
            "card": PaymentMethod.CREDIT_CARD,
            "credit_card": PaymentMethod.CREDIT_CARD,
            "fawry": PaymentMethod.FAWRY,
            "meeza": PaymentMethod.MEEZA,
            "vodafone": PaymentMethod.VODAFONE_CASH,
            "vodafone_cash": PaymentMethod.VODAFONE_CASH,
            "bank_transfer": PaymentMethod.BANK_TRANSFER,
            "wallet": PaymentMethod.WALLET,

            # Numeric ids (per ACTIVATE_PAYMENT_METHODS.md)
            "1": PaymentMethod.CREDIT_CARD,
            "2": PaymentMethod.FAWRY,
            "3": PaymentMethod.MEEZA,
            "4": PaymentMethod.VODAFONE_CASH,
            "5": PaymentMethod.BANK_TRANSFER,
        }

        return method_map.get(ms)

    # --------------------------------------------------------------------------
    # Card Vault (Tokenization) Methods
    # --------------------------------------------------------------------------
    
    def initiate_card_tokenization(self, user_id: str) -> str:
        """
        Get URL for adding a new card.
        """
        from modules.users.models import User
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException("User not found")
            
        user_data = {
            "id": str(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name or "",
            "email": user.email,
            "phone": user.phone or ""
        }
        
        # We need a success URL where the mobile app can intercept
        # In a real app, this should be a deep link, but Fawaterk might require http/https
        # We will use our success page which the mobile app can capture
        redirect_url = settings.PAYMENT_SUCCESS_URL
        
        return self.fawaterk.create_card_token_url(user_data, redirect_url)

    def get_user_cards(self, user_id: str):
        """List saved cards for user"""
        from modules.payments.models import UserCard
        return self.db.query(UserCard).filter(
            UserCard.user_id == user_id,
            UserCard.is_active == True
        ).order_by(UserCard.created_at.desc()).all()

    def delete_user_card(self, user_id: str, card_id: str):
        """Delete (deactivate) a saved card"""
        from modules.payments.models import UserCard
        card = self.db.query(UserCard).filter(
            UserCard.id == card_id,
            UserCard.user_id == user_id
        ).first()
        
        if not card:
            raise NotFoundException("Card not found")
            
        # Hard delete or soft delete? Soft delete preferred for history
        card.is_active = False
        self.db.commit()
        return True

    def process_token_webhook(self, payload: Dict[str, Any]):
        """
        Special handler for Tokenization Webhook.
        Values might appear in 'data' or root depending on API version.
        """
        from modules.payments.models import UserCard
        
        logger.info(f"🔵 Processing Token Webhook: {payload}")
        
        # Extract data (adjust keys based on actual payload observation)
        # Expected: customer_unique_id, token, card_info (last4, brand, expiry)
        
        customer_id = payload.get("customer_unique_id") or payload.get("customer", {}).get("unique_id")
        token = payload.get("token") or payload.get("card_token")
        card_data = payload.get("card_data", {}) or payload.get("card", {})
        
        if not customer_id or not token:
            logger.warning("⚠️ Token webhook missing required fields")
            return
            
        # Check if card already exists
        existing = self.db.query(UserCard).filter(
            UserCard.provider_token == token
        ).first()
        
        if existing:
            logger.info("ℹ️ Card already tokenized")
            return

        # Create new card
        new_card = UserCard(
            id=str(uuid4()),
            user_id=customer_id, # Assuming we passed user.id as unique_id
            provider="FAWATERK",
            provider_token=token,
            card_mask=f"xxxx-xxxx-xxxx-{card_data.get('lastFourDigits', '0000')}",
            last4=card_data.get('lastFourDigits', '0000'),
            brand=card_data.get('brand', 'Unknown'),
            expiry_month=card_data.get('expiryMonth'),
            expiry_year=card_data.get('expiryYear'),
            holder_name=payload.get("customer", {}).get("first_name"),
            is_active=True
        )
        
        self.db.add(new_card)
        self.db.commit()
        logger.info(f"✅ Card tokenized for user {customer_id}")
