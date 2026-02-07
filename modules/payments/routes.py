from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List
import logging

from database.base import get_db
from config.settings import settings
from modules.payments.service import PaymentService
from modules.payments.schemas import CreatePaymentRequest, CreatePaymentResponse, UserCardResponse, InitCardTokenResponse
from modules.payments.models import Payment, PaymentWebhookLog
from shared.exceptions import PaymentException, NotFoundException
from shared.dependencies import get_admin_user, get_current_user, require_active_membership

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/create", response_model=CreatePaymentResponse)
def create_payment(
    payment_data: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_active_membership)
):
    """
    Initiate a payment for an Order or Booking.
    """
    payment_service = PaymentService(db)
    # Check if this is for an order or booking
    if payment_data.order_id:
        return payment_service.initiate_order_payment(
            order_id=payment_data.order_id,
            user_id=current_user.id,
            payment_method_id=payment_data.payment_method_id,
            success_url=settings.PAYMENT_SUCCESS_URL,
            fail_url=settings.PAYMENT_FAIL_URL,
            save_card=payment_data.save_card
        )
    elif payment_data.booking_id:
        return payment_service.initiate_booking_payment(
            booking_id=payment_data.booking_id,
            user_id=current_user.id,
            payment_method_id=payment_data.payment_method_id,
            success_url=settings.PAYMENT_SUCCESS_URL,
            fail_url=settings.PAYMENT_FAIL_URL,
            save_card=payment_data.save_card
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either order_id or booking_id must be provided"
        )


@router.get("/debug-fawaterk")
def debug_fawaterk(amount: float = 100, currency: str = "USD", key: str = ""):
    """
    Call Fawaterk with minimal payload and return raw response (status_code, response_text, request_payload).
    To use: set DEBUG_FAWATERK_KEY in .env then open .../debug-fawaterk?key=YOUR_KEY
    Or when DEBUG=true, no key needed.
    """
    if not settings.DEBUG and getattr(settings, "DEBUG_FAWATERK_KEY", None) != key:
        raise HTTPException(status_code=404, detail="Not available")
    from modules.payments.fawaterk_service import FawaterkService
    svc = FawaterkService()
    result = svc.debug_invoice_request(amount=amount, currency=currency)
    return result


@router.post("/fawaterk/webhook")
async def fawaterk_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Fawaterk payment notifications.
    
    This endpoint:
    1. Receives webhook from Fawaterk
    2. Verifies the hash signature (HMAC SHA256)
    3. Processes payment state (PAID/FAILED/EXPIRED)
    4. Ensures idempotency (ignores duplicate events)
    
    Security: Webhook is verified using FAWATERK_VENDOR_KEY
    """
    try:
        # Get raw payload
        payload = await request.json()
        
        logger.info(f"🔵 Fawaterk webhook received: {payload}")
        
        # Process webhook
        payment_service = PaymentService(db)
        result = payment_service.handle_fawaterk_webhook(payload)
        
        return {"status": "success", "data": result}
    
    except PaymentException as e:
        logger.error(f"❌ Payment exception: {e.detail}")
        raise
    
    except NotFoundException as e:
        logger.error(f"❌ Not found: {e.detail}")
        raise
    
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@router.get("/status/{payment_id}")
def get_payment_status(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    Get payment status by ID.
    Used by mobile app to poll payment status after returning from WebView.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    
    if not payment:
        raise NotFoundException("Payment not found")
    
    return {
        "payment_id": str(payment.id),
        "payment_number": payment.payment_number,
        "status": payment.status.value,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        "error_message": payment.error_message
    }


@router.get("/success", response_class=HTMLResponse)
def payment_success(request: Request):
    """
    HTML landing page for successful payments.
    Fawaterk redirects here.
    """
    return """
    <html>
        <head>
            <title>Payment Successful</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #f0fdf4; color: #166534; }
                .card { background: white; padding: 2rem; border-radius: 1rem; shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center; }
                h1 { margin-top: 0; }
                .btn { display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #22c55e; color: white; text-decoration: none; border-radius: 0.5rem; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>✅ تم الدفع بنجاح</h1>
                <p>شكراً لك! سيتم تحويلك الآن للعودة للتطبيق.</p>
                <a href="altayarvip://payment/success" class="btn">العودة للتطبيق</a>
            </div>
            <script>
                // Try to auto-redirect after 2 seconds
                setTimeout(function() {
                    window.location.href = "altayarvip://payment/success";
                }, 2000);
            </script>
        </body>
    </html>
    """


@router.get("/fail", response_class=HTMLResponse)
def payment_fail(request: Request):
    """
    HTML landing page for failed payments.
    Fawaterk redirects here.
    """
    return """
    <html>
        <head>
            <title>Payment Failed</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #fef2f2; color: #991b1b; }
                .card { background: white; padding: 2rem; border-radius: 1rem; shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center; }
                h1 { margin-top: 0; }
                .btn { display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #ef4444; color: white; text-decoration: none; border-radius: 0.5rem; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>❌ فشل الدفع</h1>
                <p>نعتذر، حدثت مشكلة أثناء معالجة الدفع.</p>
                <a href="altayarvip://payment/fail" class="btn">العودة للتطبيق</a>
            </div>
            <script>
                // Try to auto-redirect after 2 seconds
                setTimeout(function() {
                    window.location.href = "altayarvip://payment/fail";
                }, 2000);
            </script>
        </body>
    </html>
    """


@router.get("/pay-later", response_class=HTMLResponse)
def payment_pay_later(
    payment_id: str,
    db: Session = Depends(get_db)
):
    """
    صفحة الدفع لاحقاً: عندما فشل Fawaterk نرسل المستخدم هنا ليتم الحجز ويدفع يدوياً.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    amount = "—"
    currency = ""
    if payment:
        amount = str(float(payment.amount))
        currency = payment.currency or "USD"
    html = f"""
    <!DOCTYPE html>
    <html dir="rtl" lang="ar">
        <head>
            <meta charset="utf-8">
            <title>الدفع لاحقاً - AltayarVIP</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; margin: 0; background: #f0f9ff; color: #0f172a; padding: 1rem; }}
                .card {{ background: white; padding: 2rem; border-radius: 1rem; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); text-align: center; max-width: 400px; }}
                h1 {{ margin-top: 0; color: #1071b8; }}
                .amount {{ font-size: 1.25rem; margin: 1rem 0; }}
                .btn {{ display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #1071b8; color: white; text-decoration: none; border-radius: 0.5rem; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>تم تسجيل طلبك</h1>
                <p>تم إنشاء الحجز بنجاح. المبلغ: <span class="amount">{amount} {currency}</span></p>
                <p>للدفع: سنتواصل معك قريباً، أو يمكنك الاتصال بنا لإتمام الدفع.</p>
                <a href="altayarvip://payment/success" class="btn">العودة للتطبيق</a>
            </div>
            <script>
                setTimeout(function() {{ window.location.href = "altayarvip://payment/success"; }}, 3000);
            </script>
        </body>
    </html>
    """
    return HTMLResponse(html)


@router.get("/webhook-logs")
def get_webhook_logs(
    invoice_id: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get webhook logs for debugging (admin only in production).
    """
    query = db.query(PaymentWebhookLog).order_by(PaymentWebhookLog.created_at.desc())
    
    if invoice_id:
        query = query.filter(PaymentWebhookLog.invoice_id == invoice_id)
    
    logs = query.limit(limit).all()
    
    return {
        "count": len(logs),
        "logs": [
            {
                "id": str(log.id),
                "provider": log.provider,
                "event_type": log.event_type,
                "invoice_id": log.invoice_id,
                "is_valid": log.is_valid,
                "processed": log.processed,
                "processed_at": log.processed_at.isoformat() if log.processed_at else None,
                "error_message": log.error_message,
                "processing_time_ms": log.processing_time_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }




@router.get("", response_model=Dict[str, Any])
def list_all_payments(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_admin_user)
):
    """
    List all payments (Admin only).
    Includes both booking-based and order-based payments.
    """
    from modules.orders.models import Order, PaymentStatus as OrderPaymentStatus
    from modules.bookings.models import Booking
    
    # Fetch Payments
    payment_query = db.query(Payment)
    if status:
        payment_query = payment_query.filter(Payment.status == status)
    
    payment_total = payment_query.count()
    payments = payment_query.options(joinedload(Payment.user)).order_by(Payment.created_at.desc()).limit(offset + limit).all()
    
    # Fetch Orders (Invoices) - only those NOT linked to payments
    order_query = db.query(Order).filter(
        ~Order.id.in_(
            db.query(Payment.order_id).filter(Payment.order_id.isnot(None))
        )
    )
    
    if status:
        # Map generic payment status to Order payment status
        if status in ['PAID', 'PENDING', 'FAILED']:
            if status == 'PAID':
                order_query = order_query.filter(Order.payment_status == OrderPaymentStatus.PAID)
            elif status == 'PENDING':
                order_query = order_query.filter(Order.payment_status.in_([OrderPaymentStatus.UNPAID, OrderPaymentStatus.PARTIALLY_PAID]))
        
    order_total = order_query.count()
    orders = order_query.options(joinedload(Order.user)).order_by(Order.created_at.desc()).limit(offset + limit).all()

    # Build combined items list
    combined_items = []
    
    for p in payments:
        item = {
            "id": str(p.id),
            "payment_number": p.payment_number,
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status.value,
            "payment_method": p.payment_method.value if hasattr(p.payment_method, "value") and p.payment_method else None,
            "created_at": p.created_at,
            "source": "PAYMENT",
            "payment_type": p.payment_type.value if hasattr(p.payment_type, "value") else None,
            "user_id": str(p.user_id) if p.user_id else None,
            "user": {
                "first_name": p.user.first_name,
                "last_name": p.user.last_name,
                "email": p.user.email
            } if p.user else None
        }
        
        # Add booking details if payment is linked to a booking
        if p.booking_id:
            booking = db.query(Booking).filter(Booking.id == p.booking_id).first()
            if booking:
                item["booking"] = {
                    "id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
                    "title_en": booking.title_en,
                    "title_ar": booking.title_ar,
                    "start_date": booking.start_date.isoformat() if booking.start_date else None,
                    "end_date": booking.end_date.isoformat() if booking.end_date else None,
                }
        
        # Add order details if payment is linked to an order
        if p.order_id:
            order = db.query(Order).filter(Order.id == p.order_id).first()
            if order:
                item["order"] = {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "notes_en": order.notes_en,
                    "notes_ar": order.notes_ar,
                }
        
        combined_items.append(item)

    # Add standalone orders (not linked to any payment)
    for o in orders:
        combined_items.append({
            "id": str(o.id),
            "payment_number": o.order_number,  # Use order number as payment number
            "amount": float(o.total_amount),
            "currency": o.currency or "USD",
            "status": o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status),
            "payment_method": "INVOICE",
            "created_at": o.created_at,
            "source": "INVOICE",
            "payment_type": "ORDER",
            "user_id": str(o.user_id) if o.user_id else None,
            "user": {
                "first_name": o.user.first_name,
                "last_name": o.user.last_name,
                "email": o.user.email
            } if o.user else None,
            "order": {
                "id": str(o.id),
                "order_number": o.order_number,
                "notes_en": o.notes_en,
                "notes_ar": o.notes_ar,
            }
        })

    # Sort descending by date
    combined_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Slice for pagination
    paged_items = combined_items[offset : offset + limit]
    
    # Convert datetime objects to strings for response
    final_items = []
    for item in paged_items:
        item['created_at'] = item['created_at'].isoformat()
        final_items.append(item)

    return {
        "total": payment_total + order_total,
        "items": final_items
    }


@router.get("/{payment_id}")
def get_payment_details(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_admin_user)
):
    """
    Get detailed information about a specific payment (Admin only).
    """
    try:
        logger.info(f"[PaymentDetails] Fetching payment details for ID: {payment_id}")
        logger.info(f"[PaymentDetails] Requested by user: {current_user.email} (Role: {current_user.role})")
        
        from modules.orders.models import Order
        from modules.bookings.models import Booking
        
        # Try to find payment
        logger.debug(f"[PaymentDetails] Querying Payment table for ID: {payment_id}")
        payment = db.query(Payment).options(joinedload(Payment.user)).filter(
            Payment.id == payment_id
        ).first()
    
        if payment:
            logger.info(f"[PaymentDetails] Found payment with ID: {payment_id}")
            # Build payment response
            result = {
                "id": str(payment.id),
                "payment_number": payment.payment_number,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status.value,
                "payment_method": payment.payment_method.value if hasattr(payment.payment_method, "value") and payment.payment_method else None,
                "payment_type": payment.payment_type.value if hasattr(payment.payment_type, "value") else None,
                "source": "PAYMENT",
                "transaction_id": payment.provider_transaction_id,  # Fixed: use provider_transaction_id
                "description": getattr(payment, 'description', None),  # Safe access with getattr
                "created_at": payment.created_at.isoformat(),
                "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
                "user_id": str(payment.user_id) if payment.user_id else None,
                "user": {
                    "id": str(payment.user.id),
                    "first_name": payment.user.first_name,
                    "last_name": payment.user.last_name,
                    "email": payment.user.email,
                    "phone": payment.user.phone
                } if payment.user else None
            }
            
            # Add booking details if linked
            if payment.booking_id:
                booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
                if booking:
                    result["booking"] = {
                        "id": str(booking.id),
                        "booking_number": booking.booking_number,
                        "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
                        "title_en": booking.title_en,
                        "title_ar": booking.title_ar,
                        "start_date": booking.start_date.isoformat() if booking.start_date else None,
                        "end_date": booking.end_date.isoformat() if booking.end_date else None,
                    }
            
            # Add order details if linked
            if payment.order_id:
                order = db.query(Order).filter(Order.id == payment.order_id).first()
                if order:
                    result["order"] = {
                        "id": str(order.id),
                        "order_number": order.order_number,
                        "notes_en": order.notes_en,
                        "notes_ar": order.notes_ar,
                    }
                    result["order_id"] = str(order.id)
            
            return result
        
        # If not found as payment, try to find as order (invoice)
        logger.debug(f"[PaymentDetails] Payment not found, checking Order table for ID: {payment_id}")
        order = db.query(Order).options(joinedload(Order.user)).filter(
            Order.id == payment_id
        ).first()
        
        if order:
            logger.info(f"[PaymentDetails] Found order (invoice) with ID: {payment_id}")
            return {
                "id": str(order.id),
                "payment_number": order.order_number,
                "amount": float(order.total_amount),
                "currency": order.currency or "USD",
                "status": order.payment_status.value if hasattr(order.payment_status, "value") else str(order.payment_status),
                "payment_method": "INVOICE",
                "payment_type": "ORDER",
                "source": "INVOICE",
                "description": order.notes_en or order.notes_ar,
                "created_at": order.created_at.isoformat(),
                "user_id": str(order.user_id) if order.user_id else None,
                "user": {
                    "id": str(order.user.id),
                    "first_name": order.user.first_name,
                    "last_name": order.user.last_name,
                    "email": order.user.email,
                    "phone": order.user.phone
                } if order.user else None,
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "notes_en": order.notes_en,
                    "notes_ar": order.notes_ar,
                },
                "order_id": str(order.id)
            }
        
        # Not found
        logger.warning(f"[PaymentDetails] Payment or order with ID {payment_id} not found")
        raise NotFoundException(f"Payment or order with ID {payment_id} not found")
    
    except NotFoundException as e:
        logger.error(f"[PaymentDetails] Not found error: {str(e)}")
        raise
    except HTTPException as e:
        logger.error(f"[PaymentDetails] HTTP exception: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        logger.error(f"[PaymentDetails] Unexpected error fetching payment {payment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch payment details: {str(e)}"
        )



@router.get("/my-payments")
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Get current user's payments and unpaid orders.
    Returns:
    1. All Payment records (Bookings & Orders that are paid/pending)
    2. Unpaid Orders (Invoices) that don't have a payment record yet
    """
    from modules.payments.models import PaymentStatus
    from modules.bookings.models import Booking
    from modules.orders.models import Order, PaymentStatus as OrderPaymentStatus
    
    # 1. Fetch Payments
    payments = db.query(Payment).options(joinedload(Payment.user)).filter(
        Payment.user_id == current_user.id
    ).order_by(Payment.created_at.desc()).all()
    
    # 2. Fetch Unpaid Orders (Invoices) NOT in Payments
    # Using the same logic as admin list to exclude orders that have a payment
    order_query = db.query(Order).options(joinedload(Order.user)).filter(
        Order.user_id == current_user.id,
        ~Order.id.in_(
            db.query(Payment.order_id).filter(
                Payment.order_id.isnot(None),
                Payment.user_id == current_user.id # ensure user scope
            )
        )
    )
    orders = order_query.order_by(Order.created_at.desc()).all()
    
    combined_items = []
    
    # Process Payments
    for p in payments:
        item = {
            "id": str(p.id),
            "payment_number": p.payment_number,
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status.value,
            "payment_method": p.payment_method.value if hasattr(p.payment_method, "value") and p.payment_method else None,
            "created_at": p.created_at.isoformat(),
            "source": "PAYMENT",
            "payment_type": p.payment_type.value if hasattr(p.payment_type, "value") else None,
        }
        
        # Add booking details
        if p.booking_id:
            booking = db.query(Booking).filter(Booking.id == p.booking_id).first()
            if booking:
                item["booking"] = {
                    "id": str(booking.id),
                    "booking_number": booking.booking_number,
                    "title_en": booking.title_en,
                    "title_ar": booking.title_ar,
                    "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
                    "start_date": booking.start_date.isoformat() if booking.start_date else None,
                    "end_date": booking.end_date.isoformat() if booking.end_date else None,
                }
        
        # Add order details
        if p.order_id:
            order = db.query(Order).filter(Order.id == p.order_id).first()
            if order:
                item["order"] = {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "notes_en": order.notes_en,
                    "notes_ar": order.notes_ar,
                }
        
        combined_items.append(item)
        
    # Process Unpaid Orders
    for o in orders:
        combined_items.append({
            "id": str(o.id),
            "payment_number": o.order_number, # Use order number as payment number
            "amount": float(o.total_amount),
            "currency": o.currency or "USD",
            "status": o.payment_status.value if hasattr(o.payment_status, "value") else str(o.payment_status),
            "payment_method": "INVOICE",
            "created_at": o.created_at.isoformat(),
            "source": "INVOICE",
            "payment_type": "ORDER",
            "order": {
                "id": str(o.id),
                "order_number": o.order_number,
                "notes_en": o.notes_en,
                "notes_ar": o.notes_ar,
            }
        })
        
    # Sort combined list by date desc
    combined_items.sort(key=lambda x: x['created_at'], reverse=True)
    
    return {"items": combined_items, "total": len(combined_items)}


@router.post("/complete/{payment_id}")
def complete_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user)
):
    """
    Mark a payment as completed (for manual/cash payments).
    This is called when user confirms they've paid via cash/bank transfer.
    """
    from modules.payments.models import PaymentStatus
    from modules.bookings.models import Booking, PaymentStatus as BookingPaymentStatus
    from datetime import datetime
    
    # Get payment
    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.user_id == current_user.id
    ).first()
    
    if not payment:
        raise NotFoundException("Payment not found")
    
    if payment.status != PaymentStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment is not pending"
        )
    
    # Update payment status
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.utcnow()
    
    # Update associated booking if exists
    if payment.booking_id:
        booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
        if booking:
            booking.payment_status = BookingPaymentStatus.PAID
            booking.paid_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "status": "success",
        "message": "Payment completed successfully",
        "payment_id": str(payment.id)
    }


@router.get("/cards", response_model=List[UserCardResponse])
def list_saved_cards(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_active_membership)
):
    """List all saved cards for the current user"""
    payment_service = PaymentService(db)
    return payment_service.get_user_cards(current_user.id)


@router.post("/cards/init", response_model=InitCardTokenResponse)
def init_add_card(
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_active_membership)
):
    """Get the URL to add a new card via tokenization"""
    payment_service = PaymentService(db)
    url = payment_service.initiate_card_tokenization(current_user.id)
    return {"url": url}


@router.delete("/cards/{card_id}")
def delete_saved_card(
    card_id: str,
    db: Session = Depends(get_db),
    current_user: Any = Depends(require_active_membership)
):
    """Delete a saved card"""
    payment_service = PaymentService(db)
    payment_service.delete_user_card(current_user.id, card_id)
    return {"status": "success", "message": "Card deleted"}
