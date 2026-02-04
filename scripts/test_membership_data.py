#!/usr/bin/env python3
"""
Test to verify membership data is properly saved and points are awarded
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
from modules.points.models import PointsBalance, PointsTransaction
from modules.users.models import User

def test_membership_data_integrity():
    """Test that membership data is properly saved"""

    db = SessionLocal()
    try:
        service = UserIntegrationService(db)

        # Get the Silver plan (1500 points)
        silver_plan = db.query(MembershipPlan).filter(MembershipPlan.tier_name_en == "Silver Membership").first()
        if not silver_plan:
            print('❌ لم توجد خطة Silver Membership')
            return False

        perks = silver_plan.perks
        if isinstance(perks, str):
            perks = json.loads(perks)
        points = perks.get('points', 0) if isinstance(perks, dict) else 0
        print(f'✅ وُجدت خطة Silver: {silver_plan.tier_name_en} مع {points} نقطة')

        # Create a test user with Silver membership
        user_data = {
            'email': f'data_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'datatest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Data',
            'last_name': 'Test',
            'plan_id': str(silver_plan.id)
        }

        print('🧪 إنشاء مستخدم مع عضوية Silver...')
        result = service.create_user_with_membership(user_data, created_by_admin=True)

        user_id = result['user']['id']
        print(f'✅ تم إنشاء المستخدم: {result["user"]["email"]}')

        # Check 1: Verify subscription was created with correct data
        subscription = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).first()

        if not subscription:
            print('❌ لم يتم إنشاء الاشتراك')
            return False

        print(f'✅ تم إنشاء الاشتراك: {subscription.membership_number}')
        print(f'   - تاريخ البداية: {subscription.start_date}')
        print(f'   - تاريخ النهاية: {subscription.expiry_date}')
        print(f'   - الحالة: {subscription.status.value}')

        # Check 2: Verify points were awarded
        points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
        if not points_balance:
            print('❌ لم يتم إنشاء رصيد النقاط')
            return False

        print(f'✅ رصيد النقاط: {points_balance.current_balance} نقطة')
        print(f'   - النقاط المكتسبة: {points_balance.total_earned}')
        print(f'   - النقاط المستبدلة: {points_balance.total_redeemed}')

        # Check 3: Verify points transaction was created
        transaction = db.query(PointsTransaction).filter(
            PointsTransaction.user_id == user_id,
            PointsTransaction.transaction_type == "BONUS"
        ).first()

        if not transaction:
            print('❌ لم يتم إنشاء معاملة النقاط')
            return False

        print(f'✅ تم إنشاء معاملة النقاط:')
        print(f'   - النوع: {transaction.transaction_type.value}')
        print(f'   - النقاط: {transaction.points}')
        print(f'   - الوصف: {transaction.description_en}')

        # Verify expected values
        expected_points = 1500  # Silver membership welcome points

        if subscription.expiry_date is not None:
            print('⚠️ تحذير: يجب أن تكون تاريخ النهاية None للعضويات غير المحدودة')

        if points_balance.current_balance != expected_points:
            print(f'❌ خطأ: الرصيد الحالي {points_balance.current_balance} يجب أن يكون {expected_points}')
            return False

        if transaction.points != expected_points:
            print(f'❌ خطأ: معاملة النقاط {transaction.points} يجب أن تكون {expected_points}')
            return False

        print('🎉 جميع اختبارات البيانات نجحت!')
        print(f'✅ العضوية: {silver_plan.tier_name_en}')
        print(f'✅ النقاط: {expected_points}')
        print(f'✅ تاريخ النهاية: {subscription.expiry_date or "غير محدد (عضوية دائمة)"}')

        return True

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_membership_data_integrity()
    print('🎉 الاختبار نجح!' if success else '❌ الاختبار فشل!')
    sys.exit(0 if success else 1)
