import sys
import os

sys.path.insert(0, os.getcwd())

from database.base import SessionLocal
from modules.users.models import User
# Ensure all models are imported
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus
from modules.wallet.models import Wallet
from modules.points.models import PointsBalance

db = SessionLocal()

try:
    print("\n" + "="*50)
    print("SIMULATING API GET /ADMIN/USERS")
    print("="*50)
    
    users = db.query(User).all()
    print(f"Total Users: {len(users)}\n")
    
    for u in users:
        print(f"Processing user: {u.email} (ID: {u.id})")
        
        # 1. Check Subscriptions
        latest_sub = None
        if hasattr(u, "subscriptions") and u.subscriptions:
            print(f"  - Found {len(u.subscriptions)} subscriptions")
            sorted_subs = sorted(u.subscriptions, key=lambda s: s.created_at, reverse=True)
            latest_sub = sorted_subs[0] if sorted_subs else None
        else:
            print("  - No subscriptions found")

        plan_info = None
        subscription_info = None
        
        if latest_sub:
            print(f"  - Latest Sub: {latest_sub.id}, Status: {latest_sub.status}")
            if latest_sub.plan:
                print(f"  - Plan: {latest_sub.plan.tier_name_en}")
                plan_info = {
                    "name": latest_sub.plan.tier_name_en,
                    "code": latest_sub.plan.tier_code,
                    "color": latest_sub.plan.color_hex
                }
            else:
                print("  - NO PLAN LINKED!")
                
            subscription_info = {
                "status": str(latest_sub.status),
                "membership_id": latest_sub.membership_number
            }

        # 2. Check Enums
        role_val = u.role.value if hasattr(u.role, 'value') else str(u.role)
        status_val = u.status.value if hasattr(u.status, 'value') else str(u.status)
        
        print(f"  - Role: {role_val}")
        print(f"  - Status: {status_val}")
        print("  - OK")
        print("-" * 30)

    print("\nSUCCESS! No errors found.")

except Exception as e:
    print(f"\nCRASHED! Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    db.close()
