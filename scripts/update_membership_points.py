# تحديث النقاط الأساسية للعضويات
# Update Initial Points for Membership Plans

"""
هذا السكريبت يوضح كيفية تحديث النقاط الأساسية لكل عضوية.
This script shows how to update initial points for each membership plan.

بعد تشغيل الـ migration، قم بتحديث قيم initial_points لكل عضوية:
After running the migration, update the initial_points values for each membership:
"""

# مثال على القيم:
# Example values:

MEMBERSHIP_INITIAL_POINTS = {
    "SILVER": {
        "price": 2000,  # USD
        "initial_points": 1500,
        "points_value": 1.33  # 2000 / 1500 = 1.33 USD per point
    },
    "GOLD": {
        "price": 5000,
        "initial_points": 4000,
        "points_value": 1.25  # 5000 / 4000 = 1.25 USD per point
    },
    "PLATINUM": {
        "price": 10000,
        "initial_points": 8500,
        "points_value": 1.18  # 10000 / 8500 = 1.18 USD per point
    },
    "VIP": {
        "price": 20000,
        "initial_points": 18000,
        "points_value": 1.11  # 20000 / 18000 = 1.11 USD per point
    },
    "DIAMOND": {
        "price": 50000,
        "initial_points": 47000,
        "points_value": 1.06  # 50000 / 47000 = 1.06 USD per point
    }
}

# SQL لتحديث القيم:
# SQL to update values:

"""
-- Silver Membership
UPDATE membership_plans 
SET initial_points = 1500 
WHERE tier_code = 'SILVER';

-- Gold Membership
UPDATE membership_plans 
SET initial_points = 4000 
WHERE tier_code = 'GOLD';

-- Platinum Membership
UPDATE membership_plans 
SET initial_points = 8500 
WHERE tier_code = 'PLATINUM';

-- VIP Membership
UPDATE membership_plans 
SET initial_points = 18000 
WHERE tier_code = 'VIP';

-- Diamond Membership
UPDATE membership_plans 
SET initial_points = 47000 
WHERE tier_code = 'DIAMOND';
"""

# أو استخدم Python script:
# Or use Python script:

"""
from sqlalchemy.orm import Session
from modules.memberships.models import MembershipPlan
from database.base import get_db

def update_membership_initial_points():
    db = next(get_db())
    
    for tier_code, data in MEMBERSHIP_INITIAL_POINTS.items():
        plan = db.query(MembershipPlan).filter(
            MembershipPlan.tier_code == tier_code
        ).first()
        
        if plan:
            plan.initial_points = data['initial_points']
            print(f"Updated {tier_code}: {data['initial_points']} points (value: {data['points_value']:.2f} USD/point)")
    
    db.commit()
    print("✅ All membership plans updated successfully!")

if __name__ == "__main__":
    update_membership_initial_points()
"""
