#!/usr/bin/env python3
"""Quick script to check bookings in database"""

from database.base import SessionLocal
from modules.bookings.models import Booking
from modules.users.models import User

db = SessionLocal()

try:
    # Get all bookings
    bookings = db.query(Booking).all()
    print(f"\n{'='*60}")
    print(f"TOTAL BOOKINGS IN DATABASE: {len(bookings)}")
    print(f"{'='*60}\n")
    
    if bookings:
        for booking in bookings:
            print(f"Booking: {booking.booking_number}")
            print(f"  ID: {booking.id}")
            print(f"  User ID: {booking.user_id}")
            print(f"  Status: {booking.status}")
            print(f"  Deleted: {booking.deleted_at}")
            print(f"  Created: {booking.created_at}")
            
            # Get user info
            user = db.query(User).filter(User.id == booking.user_id).first()
            if user:
                print(f"  User: {user.email} ({user.first_name} {user.last_name})")
                print(f"  User Role: {user.role}")
            else:
                print(f"  User: NOT FOUND!")
            print()
    else:
        print("No bookings found in database!")
        
    # Check users
    print(f"\n{'='*60}")
    print("ALL USERS:")
    print(f"{'='*60}\n")
    users = db.query(User).all()
    for user in users:
        print(f"  {user.email} (ID: {user.id}, Role: {user.role})")
    
finally:
    db.close()
