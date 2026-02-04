import sys
import os
import datetime
import uuid

sys.path.insert(0, os.getcwd())

from database.base import SessionLocal
from modules.users.models import User
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus

db = SessionLocal()

try:
    print("\n--- Manually Adding Subscription ---")
    
    # 1. Get User
    user = db.query(User).filter(User.email == 'demo@altayar.com').first()
    if not user:
        print("User demo@altayar.com not found!")
        exit(1)
    
    print(f"User found: {user.email} (ID: {user.id})")
    
    # 2. Get Plan (Silver)
    plan = db.query(MembershipPlan).first() # Get the first available plan
    if not plan:
        print("No membership plans found in DB!")
        exit(1)
        
    print(f"Plan found: {plan.tier_name_en} (ID: {plan.id})")
    
    # 3. Create Subscription
    # Check if already exists
    if db.query(MembershipSubscription).filter(MembershipSubscription.user_id == user.id).first():
        print("User already has a subscription!")
    else:
        new_sub = MembershipSubscription(
            user_id=user.id,
            plan_id=plan.id,
            start_date=datetime.datetime.utcnow(),
            end_date=datetime.datetime.utcnow() + datetime.timedelta(days=365),
            status=MembershipStatus.ACTIVE,
            price_paid=plan.price,
            payment_status="PAID",
            membership_number=f"MEM-{uuid.uuid4().hex[:8].upper()}"
        )
        db.add(new_sub)
        db.commit()
        print(f"FAILED TO COMMIT? No, wait...")
        # Re-query to confirm
        if db.query(MembershipSubscription).filter(MembershipSubscription.user_id == user.id).first():
             print("SUCCESS! Subscription added successfully.")
        else:
             print("ERROR: Commit appeared successful but record not found.")

except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()
