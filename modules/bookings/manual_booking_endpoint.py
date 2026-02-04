"""
Manual booking creation endpoint - Add this to the end of routes.py
"""
from fastapi import Depends, status
from sqlalchemy.orm import Session
import uuid

from database.base import get_db
from modules.bookings.models import Booking, BookingItem, BookingStatus, BookingPaymentStatus
from modules.bookings.schemas import ManualBookingCreate
from modules.bookings.routes import booking_to_response, router
from modules.users.models import User
from shared.dependencies import get_employee_or_admin_user
from shared.exceptions import NotFoundException
from shared.utils import generate_unique_number

@router.post("/manual-create", status_code=status.HTTP_201_CREATED)
def create_manual_booking(
    booking_data: ManualBookingCreate,
    current_user: User = Depends(get_employee_or_admin_user),
    db: Session = Depends(get_db)
):
    """
    Create a manual booking from admin/employee dashboard (simplified).
    
    Handles: Simple booking creation, Points/wallet deduction, Payment tracking
    Requires: Bearer token with ADMIN, SUPER_ADMIN, or EMPLOYEE role
    """
    # Verify user exists
    user = db.query(User).filter(User.id == booking_data.user_id).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Calculate totals
    subtotal = booking_data.original_price - booking_data.discount
    points_value = booking_data.points_to_use * 1.0
    wallet_value = booking_data.wallet_to_use
    final_total = max(0, subtotal - points_value - wallet_value)
    
    # Generate booking number
    sequence = db.query(Booking).count() + 1
    booking_number = generate_unique_number("BK", sequence)
    
    # Map payment status
    payment_status_map = {
        "PAID": BookingPaymentStatus.PAID,
        "UNPAID": BookingPaymentStatus.UNPAID,
        "PARTIAL": BookingPaymentStatus.PARTIALLY_PAID
    }
    payment_status = payment_status_map.get(booking_data.payment_status, BookingPaymentStatus.UNPAID)
    
    # Create booking
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
        discount_amount=booking_data.discount + points_value + wallet_value,
        total_amount=final_total,
        currency="USD",
        payment_status=payment_status,
        title_en=f"{booking_data.booking_type}: {booking_data.destination}",
        title_ar=f"{booking_data.booking_type}: {booking_data.destination}",
        guest_count=booking_data.num_persons,
        customer_notes=booking_data.notes
    )
    
    db.add(booking)
    db.flush()
    
    # Create booking item
    item = BookingItem(
        id=str(uuid.uuid4()),
        booking_id=booking.id,
        item_type="service",
        description_ar=f"{booking_data.destination} - {booking_data.num_persons} أشخاص",
        description_en=f"{booking_data.destination} - {booking_data.num_persons} persons",
        quantity=1,
        unit_price=booking_data.original_price,
        total_price=booking_data.original_price,
        currency="USD"
    )
    db.add(item)
    
    db.commit()
    db.refresh(booking)
    
    return booking_to_response(booking, db)
