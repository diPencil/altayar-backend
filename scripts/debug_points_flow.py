#!/usr/bin/env python3
"""
Debug the points awarding flow step by step
"""

import os
import sys
import uuid
import json

# Setup environment
os.environ["DATABASE_URL"] = "sqlite:///d:/Development/altayar/MobileApp/backend/altayarvip.db"
os.environ["JWT_SECRET_KEY"] = "dummy"
os.environ["SECRET_KEY"] = "dummy"
os.environ["FAWATERK_API_KEY"] = "dummy"
os.environ["FAWATERK_VENDOR_KEY"] = "dummy"

sys.path.append(os.path.dirname(__file__))

# Import all models first
import modules

from shared.user_integration_service import UserIntegrationService
from database.base import SessionLocal
from modules.memberships.models import MembershipPlan, MembershipSubscription, MembershipStatus
from modules.points.models import PointsBalance, PointsTransaction, PointsTransactionType
from modules.points.service import PointsService
from modules.users.models import User

def debug_points_flow():
    """Debug the points awarding flow step by step"""

    db = SessionLocal()
    try:
        service = UserIntegrationService(db)

        # Get the Silver plan
        silver_plan = db.query(MembershipPlan).filter(MembershipPlan.tier_name_en == "Silver Membership").first()
        if not silver_plan:
            print('❌ لم توجد خطة Silver Membership')
            return False

        print(f'🎫 خطة Silver: {silver_plan.tier_name_en}')
        print(f'   Perks: {silver_plan.perks}')

        # Parse perks
        perks = silver_plan.perks
        if isinstance(perks, str):
            perks = json.loads(perks)
        expected_points = perks.get('points', 0) if isinstance(perks, dict) else 0
        print(f'   Welcome Points: {expected_points}')

        # Create a test user with Silver membership
        user_data = {
            'email': f'points_debug_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'pointsdebug_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Points',
            'last_name': 'Debug',
            'plan_id': str(silver_plan.id)
        }

        print(f'\\n👤 إنشاء المستخدم: {user_data["email"]}')

        # Step 1: Create user
        user = service._create_user_record(user_data, created_by_admin=True)
        db.add(user)
        db.flush()
        print(f'✅ تم إنشاء المستخدم: {user.id}')

        # Step 2: Check if points balance exists before membership
        points_balance_before = db.query(PointsBalance).filter(PointsBalance.user_id == str(user.id)).first()
        print(f'📊 رصيد النقاط قبل العضوية: {points_balance_before}')

        # Step 3: Create membership subscription manually
        print('🎫 إنشاء اشتراك العضوية...')
        subscription, points_awarded = service._create_membership_subscription(user, user_data)
        print(f'✅ تم إنشاء الاشتراك: {subscription.membership_number}')
        print(f'⭐ النقاط الممنوحة: {points_awarded}')

        # Step 4: Check points balance after membership
        points_balance_after = db.query(PointsBalance).filter(PointsBalance.user_id == str(user.id)).first()
        print(f'📊 رصيد النقاط بعد العضوية: {points_balance_after}')

        if points_balance_after:
            print(f'   - الرصيد الحالي: {points_balance_after.current_balance}')
            print(f'   - إجمالي المكتسب: {points_balance_after.total_earned}')
            print(f'   - إجمالي المستهلك: {points_balance_after.total_redeemed}')

        # Step 5: Check points transactions
        transactions = db.query(PointsTransaction).filter(PointsTransaction.user_id == str(user.id)).all()
        print(f'📝 معاملات النقاط: {len(transactions)} معاملة')

        for tx in transactions:
            print(f'   - نوع: {tx.transaction_type.value}')
            print(f'   - النقاط: {tx.points}')
            print(f'   - الوصف: {tx.description_en}')
            print(f'   - الرصيد قبل: {tx.balance_before}')
            print(f'   - الرصيد بعد: {tx.balance_after}')

        # Verify results
        success = True
        if points_awarded != expected_points:
            print(f'❌ خطأ: النقاط الممنوحة {points_awarded} لا تساوي المتوقع {expected_points}')
            success = False

        if not points_balance_after:
            print('❌ خطأ: لم يتم إنشاء رصيد النقاط')
            success = False
        elif points_balance_after.current_balance != expected_points:
            print(f'❌ خطأ: الرصيد الحالي {points_balance_after.current_balance} لا يساوي المتوقع {expected_points}')
            success = False

        if len(transactions) == 0:
            print('❌ خطأ: لم يتم إنشاء معاملات النقاط')
            success = False

        return success

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = debug_points_flow()
    print(f'\\n🎉 الاختبار {"نجح" if success else "فشل"}!')
    sys.exit(0 if success else 1)
