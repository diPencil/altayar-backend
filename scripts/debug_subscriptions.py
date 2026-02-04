import sys
import os

sys.path.insert(0, os.getcwd())

from database.base import SessionLocal
from modules.users.models import User
from modules.memberships.models import MembershipSubscription, MembershipPlan

db = SessionLocal()

try:
    print("\n" + "="*50)
    print("DEBUGGING SUBSCRIPTIONS")
    print("="*50)
    
    subs = db.query(MembershipSubscription).all()
    print(f"Total Subscriptions Found: {len(subs)}\n")
    
    for sub in subs:
        print(f"ID: {sub.id}")
        print(f"User ID: {sub.user_id}")
        print(f"Plan ID: {sub.plan_id}")
        print(f"Status: {sub.status}")
        print(f"Created At: {sub.created_at}")
        
        # Check relationships
        user = db.query(User).filter(User.id == sub.user_id).first()
        plan = db.query(MembershipPlan).filter(MembershipPlan.id == sub.plan_id).first()
        
        print(f"  -> User Found: {user.email if user else 'NO'}")
        print(f"  -> Plan Found: {plan.tier_name_en if plan else 'NO'}")
        print("-" * 30)

except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()
