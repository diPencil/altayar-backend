"""
Payment Helper Functions for Bookings

This module centralizes the logic for creating and syncing Payment records
when bookings are created or updated.
"""

from sqlalchemy.orm import Session
from datetime import datetime
import uuid
import logging

from modules.payments.models import Payment, PaymentType, PaymentStatus, PaymentProvider, PaymentMethod
from modules.bookings.models import Booking, PaymentStatus as BookingPaymentStatus

logger = logging.getLogger(__name__)


def generate_payment_number(db: Session) -> str:
    """
    Generate a unique payment number.
    Format: PAY-YYYY-XXXXXX
    """
    from datetime import datetime
    year = datetime.utcnow().year
    sequence = db.query(Payment).count() + 1
    return f"PAY-{year}-{sequence:06d}"


def create_payment_for_booking(booking: Booking, db: Session, payment_method: str = "CASH") -> Payment:
    """
    Create a Payment record for a booking.
    
    Args:
        booking: The Booking object
        db: Database session
        payment_method: Payment method string (CASH, CARD, WALLET, etc.)
        
    Returns:
        Payment: The created Payment object
    """
    try:
        # Generate payment number
        payment_number = generate_payment_number(db)
        
        # Determine payment status based on booking payment status
        payment_status = PaymentStatus.PENDING
        paid_at = None
        
        if booking.payment_status == BookingPaymentStatus.PAID:
            payment_status = PaymentStatus.PAID
            paid_at = booking.paid_at or datetime.utcnow()
        elif booking.payment_status == BookingPaymentStatus.PARTIALLY_PAID:
            payment_status = PaymentStatus.PENDING  # Treat partial as pending
        elif booking.payment_status == BookingPaymentStatus.REFUNDED:
            payment_status = PaymentStatus.REFUNDED
        
        # Map payment method string to enum
        payment_method_map = {
            "CASH": PaymentMethod.CASH,
            "CARD": PaymentMethod.CREDIT_CARD,
            "CREDIT_CARD": PaymentMethod.CREDIT_CARD,
            "DEBIT_CARD": PaymentMethod.DEBIT_CARD,
            "WALLET": PaymentMethod.WALLET,
            "BANK_TRANSFER": PaymentMethod.BANK_TRANSFER,
            "FAWRY": PaymentMethod.FAWRY,
            "MEEZA": PaymentMethod.MEEZA,
            "VODAFONE_CASH": PaymentMethod.VODAFONE_CASH,
        }
        payment_method_enum = payment_method_map.get(payment_method.upper(), PaymentMethod.CASH)
        
        # Create payment record
        payment = Payment(
            id=str(uuid.uuid4()),
            payment_number=payment_number,
            user_id=booking.user_id,
            booking_id=booking.id,
            payment_type=PaymentType.BOOKING,
            amount=booking.total_amount,
            currency=booking.currency,
            status=payment_status,
            provider=PaymentProvider.MANUAL,
            payment_method=payment_method_enum,
            paid_at=paid_at,
            payment_details={
                "booking_number": booking.booking_number,
                "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
                "title_en": booking.title_en,
                "title_ar": booking.title_ar,
                "start_date": booking.start_date.isoformat() if booking.start_date else None,
                "end_date": booking.end_date.isoformat() if booking.end_date else None,
            }
        )
        
        db.add(payment)
        db.flush()
        
        logger.info(f"✅ Created Payment {payment_number} for Booking {booking.booking_number}")
        
        return payment
        
    except Exception as e:
        logger.error(f"❌ Failed to create payment for booking {booking.booking_number}: {e}", exc_info=True)
        raise


def sync_payment_status(booking: Booking, db: Session) -> Payment:
    """
    Sync payment status with booking status.
    If no payment exists, create one.
    If payment exists, update its status.
    
    Args:
        booking: The Booking object
        db: Database session
        
    Returns:
        Payment: The synced/created Payment object
    """
    try:
        # Find existing payment for this booking
        payment = db.query(Payment).filter(
            Payment.booking_id == booking.id
        ).first()
        
        if not payment:
            # No payment exists, create one
            logger.info(f"No payment found for booking {booking.booking_number}, creating new payment")
            return create_payment_for_booking(booking, db)
        
        # Payment exists, sync status
        old_status = payment.status
        
        if booking.payment_status == BookingPaymentStatus.PAID:
            payment.status = PaymentStatus.PAID
            if not payment.paid_at:
                payment.paid_at = booking.paid_at or datetime.utcnow()
        elif booking.payment_status == BookingPaymentStatus.UNPAID:
            payment.status = PaymentStatus.PENDING
            payment.paid_at = None
        elif booking.payment_status == BookingPaymentStatus.PARTIALLY_PAID:
            payment.status = PaymentStatus.PENDING
        elif booking.payment_status == BookingPaymentStatus.REFUNDED:
            payment.status = PaymentStatus.REFUNDED
        
        # Update amount if changed
        if payment.amount != booking.total_amount:
            logger.info(f"Updating payment amount from {payment.amount} to {booking.total_amount}")
            payment.amount = booking.total_amount
        
        # Update payment details
        payment.payment_details = {
            "booking_number": booking.booking_number,
            "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else str(booking.booking_type),
            "title_en": booking.title_en,
            "title_ar": booking.title_ar,
            "start_date": booking.start_date.isoformat() if booking.start_date else None,
            "end_date": booking.end_date.isoformat() if booking.end_date else None,
        }
        
        if old_status != payment.status:
            logger.info(f"✅ Synced Payment {payment.payment_number}: {old_status.value} → {payment.status.value}")
        
        db.flush()
        
        return payment
        
    except Exception as e:
        logger.error(f"❌ Failed to sync payment for booking {booking.booking_number}: {e}", exc_info=True)
        raise


def cancel_payment_for_booking(booking: Booking, db: Session) -> None:
    """
    Cancel payment when booking is cancelled.
    
    Args:
        booking: The Booking object
        db: Database session
    """
    try:
        payment = db.query(Payment).filter(
            Payment.booking_id == booking.id
        ).first()
        
        if payment and payment.status != PaymentStatus.CANCELLED:
            payment.status = PaymentStatus.CANCELLED
            db.flush()
            logger.info(f"✅ Cancelled Payment {payment.payment_number} for Booking {booking.booking_number}")
            
    except Exception as e:
        logger.error(f"❌ Failed to cancel payment for booking {booking.booking_number}: {e}", exc_info=True)
        raise
