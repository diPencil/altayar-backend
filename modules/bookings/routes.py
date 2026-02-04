from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from database.base import get_db
from modules.bookings.models import (
    Booking, BookingItem, BookingStatusHistory,
    BookingType, BookingStatus, PaymentStatus as BookingPaymentStatus,
    BookingSource
)
from modules.bookings.schemas import (
    BookingCreate, BookingResponse, BookingListResponse, BookingStatusUpdate,
    BookingSourceFilter, ManualBookingCreate, InitiatePaymentRequest
)
from modules.bookings.payment_helper import create_payment_for_booking, sync_payment_status, cancel_payment_for_booking
from modules.users.models import User, UserRole
from shared.utils import generate_unique_number
from shared.exceptions import NotFoundException, BadRequestException
from shared.dependencies import get_current_user, get_admin_user, get_employee_or_admin_user, require_active_membership
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def compute_booking_source(booking: Booking, db: Session) -> tuple[str, str]:
    """
    Compute booking source and creator name.
    
    Returns: (booking_source, creator_name)
    """
    # If user created their own booking
    if str(booking.user_id) == str(booking.created_by_user_id):
        # Get user name
        user = db.query(User).filter(User.id == booking.user_id).first()
        creator_name = f"{user.first_name} {user.last_name}" if user else "Unknown"
        return BookingSource.SELF.value, creator_name
    
    # Get creator to determine role
    creator = db.query(User).filter(User.id == booking.created_by_user_id).first()
    if not creator:
        return BookingSource.ADMIN.value, "Unknown"
    
    creator_name = f"{creator.first_name} {creator.last_name}"
    creator_role = creator.role.value if hasattr(creator.role, 'value') else str(creator.role)
    
    if creator_role == "AGENT":
        return BookingSource.AGENT.value, creator_name
    else:
        return BookingSource.ADMIN.value, creator_name


def booking_to_response(booking: Booking, db: Session) -> dict:
    """Convert booking model to response with computed fields"""
    booking_source, creator_name = compute_booking_source(booking, db)
    
    customer = db.query(User).filter(User.id == booking.user_id).first()
    customer_name = f"{customer.first_name} {customer.last_name}" if customer else "Unknown"
    membership_id = customer.membership_id_display if customer else None
    
    return {
        "id": str(booking.id),
        "booking_number": booking.booking_number,
        "user_id": str(booking.user_id),
        "created_by_user_id": str(booking.created_by_user_id),
        "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else booking.booking_type,
        "status": booking.status.value if hasattr(booking.status, 'value') else booking.status,
        "booking_source": booking_source,
        "creator_name": creator_name,
        "customer_name": customer_name,
        "membership_id": membership_id,
        "start_date": booking.start_date.isoformat() if booking.start_date else None,
        "end_date": booking.end_date.isoformat() if booking.end_date else None,
        "subtotal": float(booking.subtotal),
        "tax_amount": float(booking.tax_amount),
        "discount_amount": float(booking.discount_amount or 0),
        "total_amount": float(booking.total_amount),
        "currency": booking.currency,
        "payment_status": booking.payment_status.value if hasattr(booking.payment_status, 'value') else booking.payment_status,
        "title_ar": booking.title_ar,
        "title_en": booking.title_en,
        "guest_count": booking.guest_count,
        "guest_names": booking.guest_names,
        "customer_notes": booking.customer_notes,
        "confirmation_number": booking.confirmation_number,
        "items": [
            {
                "id": str(item.id),
                "item_type": item.item_type,
                "description_ar": item.description_ar,
                "description_en": item.description_en,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
                "currency": item.currency,
                "item_details": item.item_details
            }
            for item in booking.items
        ],
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
        "updated_at": booking.updated_at.isoformat() if booking.updated_at else None
    }


# ============ Customer Endpoints ============

@router.get("/me")
def get_my_bookings(
    source: BookingSourceFilter = Query(default=BookingSourceFilter.ALL, description="Filter by booking source"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current customer's bookings.
    
    Filter by source:
    - all: All bookings
    - self: Self-booked only
    - admin: Admin-created only  
    - agent: Agent-created only
    
    Requires: Bearer token
    """
    logger.info(f"[get_my_bookings] Fetching bookings for user: {current_user.email} (ID: {current_user.id})")
    # Get all bookings for this user
    bookings = db.query(Booking).filter(
        Booking.user_id == str(current_user.id),
        Booking.deleted_at.is_(None)
    ).order_by(Booking.created_at.desc()).all()
    
    logger.info(f"[get_my_bookings] Found {len(bookings)} bookings for user {current_user.id}")
    
    result = []
    for booking in bookings:
        booking_source, creator_name = compute_booking_source(booking, db)
        
        # Apply source filter
        if source != BookingSourceFilter.ALL:
            if source.value.upper() != booking_source:
                continue
        
        result.append({
            "id": str(booking.id),
            "booking_number": booking.booking_number,
            "booking_type": booking.booking_type.value if hasattr(booking.booking_type, 'value') else booking.booking_type,
            "status": booking.status.value if hasattr(booking.status, 'value') else booking.status,
            "booking_source": booking_source,
            "creator_name": creator_name,
            "membership_id": current_user.membership_id_display,
            "title_en": booking.title_en,
            "title_ar": booking.title_ar,
            "total_amount": float(booking.total_amount),
            "currency": booking.currency,
            "payment_status": booking.payment_status.value if hasattr(booking.payment_status, 'value') else booking.payment_status,
            "start_date": booking.start_date.isoformat() if booking.start_date else None,
            "end_date": booking.end_date.isoformat() if booking.end_date else None,
            "created_at": booking.created_at.isoformat() if booking.created_at else None
        })
    
    logger.info(f"[get_my_bookings] Returning {len(result)} bookings after filtering")
    return result


@router.get("/{booking_id}")
def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get booking details.
    
    Requires: Bearer token
    - Customers can only see their own bookings
    - Admins can see any booking
    """
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.deleted_at.is_(None)
    ).first()
    
    if not booking:
        raise NotFoundException("Booking not found")
    
    # Check access
    user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
    if user_role == "CUSTOMER" and str(booking.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own bookings"
        )
    
    return booking_to_response(booking, db)


@router.post("/{booking_id}/pay")
def initiate_booking_payment(
    booking_id: str,
    request: InitiatePaymentRequest = None, # Optional body
    current_user: User = Depends(require_active_membership),
    db: Session = Depends(get_db)
):
    """
    Initiate payment for a booking.
    
    Requires: Bearer token
    Returns: payment_url to be opened in mobile WebView
    """
    from modules.payments.service import PaymentService
    
    payment_service = PaymentService(db)
    
    payment_method_id = request.payment_method_id if request else 1
    
    result = payment_service.initiate_booking_payment(
        booking_id=booking_id,
        user_id=str(current_user.id),
        payment_method_id=payment_method_id
    )
    
    # Notify Admin that user is attempting to pay/book
    # This covers "Book Now" click which usually leads to payment
    try:
        from modules.notifications.service import NotificationService
        from modules.notifications.models import NotificationType, NotificationTargetRole, NotificationEntityType
        from modules.notifications.schemas import NotificationCreate
        
        notification_service = NotificationService(db)
        user_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.email
        
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        booking_ref = booking.booking_number if booking else "Unknown"
        
        notification_data = NotificationCreate(
            target_role=NotificationTargetRole.ADMIN,
            target_user_id=None,
            type=NotificationType.BOOKING_UPDATED, # or PAYMENT_RECEIVED if successful, but this is initiation
            title=f"Booking Payment Initiated",
            message=f"{user_name} initiated payment for Booking {booking_ref}",
            related_entity_id=booking_id,
            related_entity_type=NotificationEntityType.BOOKING,
            action_url=f"/bookings/{booking_id}",
            triggered_by_id=str(current_user.id),
            triggered_by_role=current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
        )
        notification_service.create_notification(notification_data)
    except Exception as e:
        logger.warning(f"Failed to send payment init notification: {e}")

    return result


# ============ Admin/Employee Endpoints ============

@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_employee_or_admin_user),  # Admin or Employee
    db: Session = Depends(get_db)
):
    """
    Create a new booking for a customer.
    
    Requires: Bearer token with ADMIN, SUPER_ADMIN, or EMPLOYEE role
    """
    # Generate booking number
    sequence = db.query(Booking).count() + 1
    booking_number = generate_unique_number("BK", sequence)
    
    # Calculate totals
    subtotal = sum(item.quantity * item.unit_price for item in booking_data.items)
    tax_rate = booking_data.tax_rate or 14.0
    tax_amount = round(subtotal * (tax_rate / 100), 2)
    discount_amount = booking_data.discount_amount or 0
    total_amount = round(subtotal + tax_amount - discount_amount, 2)
    
    # Create booking
    booking = Booking(
        id=str(uuid.uuid4()),
        booking_number=booking_number,
        user_id=booking_data.user_id,
        created_by_user_id=str(current_user.id),
        offer_id=getattr(booking_data, 'offer_id', None),  # Link to offer if provided
        booking_type=booking_data.booking_type.value,
        status=BookingStatus.PENDING,
        start_date=booking_data.start_date,
        end_date=booking_data.end_date,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        currency="USD",
        payment_status=BookingPaymentStatus.UNPAID,
        title_ar=booking_data.title_ar,
        title_en=booking_data.title_en,
        description_ar=booking_data.description_ar,
        description_en=booking_data.description_en,
        guest_count=booking_data.guest_count,
        guest_names=booking_data.guest_names,
        customer_notes=booking_data.customer_notes,
        internal_notes=booking_data.internal_notes,
        booking_details=booking_data.booking_details
    )
    
    db.add(booking)
    db.flush()
    
    # Create booking items
    for item_data in booking_data.items:
        item = BookingItem(
            id=str(uuid.uuid4()),
            booking_id=booking.id,
            item_type=item_data.item_type,
            description_ar=item_data.description_ar,
            description_en=item_data.description_en,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            total_price=round(item_data.quantity * item_data.unit_price, 2),
            currency="USD",
            item_details=item_data.item_details
        )
        db.add(item)
    
    # Create initial status history
    history = BookingStatusHistory(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        old_status=None,
        new_status=BookingStatus.PENDING,
        changed_by_user_id=str(current_user.id),
        reason="Booking created"
    )
    db.add(history)
    
    # Send notifications if booking is from an offer
    # Send notifications if booking is from an offer
    if booking.offer_id:
        try:
            from modules.offers.models import Offer
            from modules.notifications.service import NotificationService
            
            offer = db.query(Offer).filter(Offer.id == booking.offer_id).first()
            if offer and offer.created_by_user_id:
                # Notify the employee who created the offer
                notification_service = NotificationService(db)
                notification_service.create_notification(
                    user_id=offer.created_by_user_id,
                    title_en=f"New Booking from Your Offer",
                    title_ar=f"حجز جديد من عرضك",
                    message_en=f"Booking {booking_number} created from your offer '{offer.title_en}'",
                    message_ar=f"تم إنشاء حجز {booking_number} من عرضك '{offer.title_ar}'",
                    notification_type="BOOKING",
                    reference_type="BOOKING",
                    reference_id=str(booking.id),
                    action_url=f"/bookings/{booking.id}"
                )
                logger.info(f"📧 Notification sent to employee {offer.created_by_user_id} for booking {booking_number}")
        except Exception as e:
            logger.error(f"Failed to send offer booking notification: {e}")
            
    # ✅ Create Payment Record using helper function
    try:
        payment = create_payment_for_booking(booking, db)
        logger.info(f"✅ Payment {payment.payment_number} created for booking {booking_number}")
    except Exception as e:
        logger.error(f"❌ Failed to create payment for booking: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create payment record: {str(e)}")
    
    db.commit()
    db.refresh(booking)
    
    logger.info(f"✅ Booking created by {current_user.email}: {booking_number}")
    
    return booking_to_response(booking, db)


@router.patch("/{booking_id}/status")
def update_booking_status(
    booking_id: str,
    status_update: BookingStatusUpdate,
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db)
):
    """
    Update booking status.
    
    Requires: Bearer token with ADMIN, SUPER_ADMIN, or EMPLOYEE role
    """
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.deleted_at.is_(None)
    ).first()
    
    if not booking:
        raise NotFoundException("Booking not found")
    
    old_status = booking.status
    new_status = status_update.status
    
    # Update status
    booking.status = new_status
    
    # Handle specific status changes
    if new_status == BookingStatus.CONFIRMED:
        booking.confirmed_at = datetime.utcnow()
    elif new_status == BookingStatus.CANCELLED:
        booking.cancelled_at = datetime.utcnow()
        booking.cancellation_reason = status_update.reason
    
    # Create status history
    history = BookingStatusHistory(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=str(current_user.id),
        reason=status_update.reason
    )
    db.add(history)
    
    # ✅ Sync or cancel payment based on booking status
    try:
        if new_status == BookingStatus.CANCELLED:
            # Cancel the payment
            cancel_payment_for_booking(booking, db)
            logger.info(f"✅ Payment cancelled for booking {booking.booking_number}")
        else:
            # Sync payment status (create if missing, update if exists)
            payment = sync_payment_status(booking, db)
            logger.info(f"✅ Payment synced for booking {booking.booking_number}")
    except Exception as e:
        logger.error(f"❌ Failed to sync payment for booking: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync payment record: {str(e)}")
    
    db.commit()
    db.refresh(booking)
    
    logger.info(f"✅ Booking {booking.booking_number} status changed: {old_status} -> {new_status}")
    
    return booking_to_response(booking, db)


@router.get("")
def list_all_bookings(
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    booking_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List all bookings (admin view).
    
    Requires: Bearer token with ADMIN, SUPER_ADMIN, or EMPLOYEE role
    """
    logger.info(f"[list_all_bookings] Fetching bookings for user: {current_user.email} (role: {current_user.role})")
    query = db.query(Booking).filter(Booking.deleted_at.is_(None))
    
    if status:
        query = query.filter(Booking.status == status)
    
    if booking_type:
        query = query.filter(Booking.booking_type == booking_type)
    
    bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()
    logger.info(f"[list_all_bookings] Found {len(bookings)} bookings in database")
    
    result = []
    for booking in bookings:
        result.append(booking_to_response(booking, db))
    
    logger.info(f"[list_all_bookings] Returning {len(result)} bookings to frontend")
    return result


# DEBUG ENDPOINT - Remove after testing
@router.get("/debug/count")
def debug_bookings_count(db: Session = Depends(get_db)):
    """Debug endpoint to check bookings count"""
    total = db.query(Booking).count()
    not_deleted = db.query(Booking).filter(Booking.deleted_at.is_(None)).count()
    return {
        "total_bookings": total,
        "not_deleted": not_deleted,
        "message": "Check server logs for details"
    }


@router.post("/manual-create", status_code=status.HTTP_201_CREATED)
def create_manual_booking(
    booking_data: ManualBookingCreate,
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db)
):
    """Create manual booking from admin dashboard (simplified)"""
    user = db.query(User).filter(User.id == booking_data.user_id).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Calculate final price WITHOUT points (only discount and wallet)
    subtotal = booking_data.original_price - booking_data.discount
    wallet_value = booking_data.wallet_to_use
    
    # Validate wallet balance
    if wallet_value > 0 and user.wallet_balance < wallet_value:
        raise BadRequestException(
            f"Insufficient wallet balance. Available: {user.wallet_balance}, Requested: {wallet_value}"
        )
    
    final_total = max(0, subtotal - wallet_value)  # ✅ No points in price calculation
    
    sequence = db.query(Booking).count() + 1
    booking_number = generate_unique_number("BK", sequence)
    
    payment_status_map = {
        "PAID": BookingPaymentStatus.PAID,
        "UNPAID": BookingPaymentStatus.UNPAID,
        "PARTIAL": BookingPaymentStatus.PARTIALLY_PAID
    }
    payment_status = payment_status_map.get(booking_data.payment_status, BookingPaymentStatus.UNPAID)
    
    # Set paid_at timestamp if booking is marked as PAID
    paid_at = datetime.utcnow() if payment_status == BookingPaymentStatus.PAID else None
    
    booking = Booking(
        id=str(uuid.uuid4()),
        booking_number=booking_number,
        user_id=booking_data.user_id,
        created_by_user_id=str(current_user.id),
        booking_type=booking_data.booking_type,
        status=BookingStatus.PENDING,
        start_date=booking_data.start_date,
        end_date=booking_data.end_date,
        subtotal=booking_data.original_price,
        tax_amount=0,
        discount_amount=booking_data.discount + wallet_value,  # ✅ No points
        total_amount=final_total,
        currency=booking_data.currency,
        payment_status=payment_status,
        paid_at=paid_at,  # ✅ Set timestamp when PAID
        title_en=f"{booking_data.booking_type}: {booking_data.destination}",
        title_ar=f"{booking_data.booking_type}: {booking_data.destination}",
        guest_count=booking_data.num_persons,
        customer_notes=booking_data.notes
    )
    
    db.add(booking)
    
    # Handle Wallet Deduction if used
    if wallet_value > 0:
        from modules.wallet.models import WalletTransaction, TransactionType, TransactionStatus
        
        wallet_tx = WalletTransaction(
            id=str(uuid.uuid4()),
            user_id=booking_data.user_id,
            amount=wallet_value,
            currency=booking_data.currency,
            transaction_type=TransactionType.PAYMENT,
            status=TransactionStatus.COMPLETED,
            description_en=f"Payment for Booking #{booking_number}",
            description_ar=f"دفع للحجز رقم {booking_number}",
            reference_id=booking.id,
            reference_type="BOOKING"
        )
        db.add(wallet_tx)
        
        # Update User Wallet Balance (Assuming user model has wallet_balance field or using service)
        # Here we rely on the wallet service/logic, but for simplicity we update the model if it exists
        if hasattr(user, 'wallet_balance'):
            user.wallet_balance -= wallet_value
            
    db.flush() # Get IDs
    
    # Create Notification for User
    from modules.notifications.models import Notification, NotificationType, NotificationTargetRole
    
    notification = Notification(
        type=NotificationType.BOOKING_CREATED,
        title="New Booking Created / تم إنشاء حجز جديد",
        message=f"New booking #{booking_number} has been created for you. / تم إنشاء حجز جديد #{booking_number} خاص بك.",
        target_user_id=booking_data.user_id,
        target_role=NotificationTargetRole.CUSTOMER,
        action_url=f"/bookings/{booking.id}",
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.add(notification)
    
    item = BookingItem(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        item_type="service",
        description_ar=f"{booking_data.destination} - {booking_data.num_persons} أشخاص",
        description_en=f"{booking_data.destination} - {booking_data.num_persons} persons",
        quantity=1,
        unit_price=booking_data.original_price,
        total_price=booking_data.original_price,
        currency=booking_data.currency
    )
    db.add(item)
    
    # Deduct wallet if used
    if wallet_value > 0:
        user.wallet_balance -= wallet_value
    
    # Handle points as SEPARATE admin action (NOT payment)
    if booking_data.points_action and booking_data.points_action in ['ADD', 'DEDUCT']:
        from modules.points.models import PointsTransaction, PointsTransactionType
        
        points_amount = booking_data.points_amount or 0
        
        if points_amount > 0:
            # Validate deduction
            if booking_data.points_action == 'DEDUCT' and user.loyalty_points < points_amount:
                raise BadRequestException(
                    f"Insufficient points to deduct. Available: {user.loyalty_points}, Requested: {points_amount}"
                )
            
            # Update user points
            balance_before = user.loyalty_points
            if booking_data.points_action == 'ADD':
                user.loyalty_points += points_amount
                transaction_type = PointsTransactionType.BONUS
                description_en = f"Points added for booking {booking_number}"
                description_ar = f"نقاط مضافة للحجز {booking_number}"
            else:  # DEDUCT
                user.loyalty_points -= points_amount
                transaction_type = PointsTransactionType.ADJUSTED
                description_en = f"Points deducted for booking {booking_number}"
                description_ar = f"نقاط مخصومة للحجز {booking_number}"
            
            balance_after = user.loyalty_points
            
            # Log points transaction
            points_transaction = PointsTransaction(
                id=str(uuid.uuid4()),
                balance_id=None,  # Will be set if PointsBalance exists
                user_id=user.id,
                transaction_type=transaction_type,
                points=points_amount if booking_data.points_action == 'ADD' else -points_amount,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type="BOOKING",
                reference_id=booking.id,
                description_en=booking_data.points_reason or description_en,
                description_ar=booking_data.points_reason or description_ar,
                created_by_user_id=current_user.id
            )
            db.add(points_transaction)
    
    # ✅ Create Payment Record using helper function
    # This ensures booking appears in both admin and user payment screens
    try:
        payment = create_payment_for_booking(booking, db, payment_method=booking_data.payment_method)
        logger.info(f"✅ Payment {payment.payment_number} created for booking {booking_number}")
    except Exception as e:
        logger.error(f"❌ Failed to create payment for booking: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create payment record: {str(e)}")

    db.commit()
    db.refresh(booking)
    
    return booking_to_response(booking, db)





@router.put("/{booking_id}")
def update_booking(
    booking_id: str,
    booking_data: ManualBookingCreate,
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db)
):
    """Update booking details"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise NotFoundException("Booking not found")
        
    # Update Allowed Fields
    # Note: We don't recalculate wallet/points logic here for simplicity unless requested
    # Just updating basic info
    booking.start_date = booking_data.start_date
    booking.end_date = booking_data.end_date
    booking.subtotal = booking_data.original_price
    booking.total_amount = max(0, booking_data.original_price - booking_data.discount - booking_data.wallet_to_use)
    booking.discount_amount = booking_data.discount + booking_data.wallet_to_use
    booking.currency = booking_data.currency
    booking.customer_notes = booking_data.notes
    booking.guest_count = booking_data.num_persons
    booking.title_en = f"{booking_data.booking_type}: {booking_data.destination}"
    booking.title_ar = f"{booking_data.booking_type}: {booking_data.destination}"
    
    # Update payment status
    payment_status_map = {
        "PAID": BookingPaymentStatus.PAID,
        "UNPAID": BookingPaymentStatus.UNPAID,
        "PARTIAL": BookingPaymentStatus.PARTIALLY_PAID
    }
    
    new_payment_status = payment_status_map.get(booking_data.payment_status, booking.payment_status)
    booking.payment_status = new_payment_status

    booking.updated_at = datetime.utcnow()
    
    # ✅ Sync Payment Record using helper function
    # This will create a payment if missing, or update existing payment status
    try:
        payment = sync_payment_status(booking, db)
        logger.info(f"✅ Payment synced for booking {booking.booking_number}")
    except Exception as e:
        logger.error(f"❌ Failed to sync payment for booking: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to sync payment record: {str(e)}")
    
    db.commit()
    db.refresh(booking)
    
    return booking_to_response(booking, db)


@router.delete("/{booking_id}")
def delete_booking(
    booking_id: str,
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db)
):
    """Soft delete a booking"""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise NotFoundException("Booking not found")
        
    booking.deleted_at = datetime.utcnow()
    # Cancel status
    booking.status = BookingStatus.CANCELLED
    
    db.commit()
    return {"success": True, "message": "Booking deleted successfully"}
