#!/usr/bin/env python3
import sys
import os
sys.path.append('.')

from database.base import SessionLocal
from modules.bookings.models import Booking
from modules.payments.models import Payment

def main():
    db = SessionLocal()
    try:
        total_bookings = db.query(Booking).count()
        not_deleted = db.query(Booking).filter(Booking.deleted_at.is_(None)).count()
        print(f'Total bookings: {total_bookings}')
        print(f'Not deleted: {not_deleted}')

        total_payments = db.query(Payment).count()
        print(f'Total payments: {total_payments}')

        # Get payments linked to bookings
        booking_payments = db.query(Payment).filter(Payment.booking_id.isnot(None)).count()
        print(f'Payments linked to bookings: {booking_payments}')

        # Get some sample bookings
        bookings = db.query(Booking).filter(Booking.deleted_at.is_(None)).limit(10).all()
        for b in bookings:
            print(f'Booking ID: {b.id}')
            print(f'  User ID: {b.user_id}')
            print(f'  Created by: {b.created_by_user_id}')
            print(f'  Booking Type: {b.booking_type}')
            print(f'  Status: {b.status}')
            print(f'  Payment Status: {b.payment_status}')
            print(f'  Number: {b.booking_number}')
            print(f'  Amount: {b.total_amount}')
            print(f'  Created: {b.created_at}')

            # Check if payment exists
            payment = db.query(Payment).filter(Payment.booking_id == b.id).first()
            if payment:
                print(f'  Payment exists: {payment.payment_number} (Status: {payment.status})')
            else:
                print('  No payment record found!')
            print('---')

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
