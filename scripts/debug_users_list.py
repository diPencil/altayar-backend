import sys
import os

# Add backend to path
sys.path.insert(0, os.getcwd())

from database.base import SessionLocal
from modules.users.models import User
# Import all other models to ensure relationships are loaded
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipHistory
from modules.entitlements.models import MembershipEntitlement, UserEntitlement, EntitlementUsageLog
from modules.wallet.models import Wallet
from modules.points.models import PointsBalance

db = SessionLocal()

try:
    print("\n" + "="*50)
    print("QUERYING ALL USERS FROM DATABASE")
    print("="*50)
    
    users = db.query(User).all()
    print(f"Total Users Found: {len(users)}\n")
    
    for u in users:
        print(f"ID: {u.id}")
        print(f"Name: {u.first_name} {u.last_name}")
        print(f"Email: {u.email}")
        print(f"Role: {u.role}")
        print(f"Status: {u.status}")
        print("-" * 30)
        
except Exception as e:
    print(f"Error querying users: {e}")
finally:
    db.close()
