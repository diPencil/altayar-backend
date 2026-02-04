#!/usr/bin/env python3
"""
Test membership upgrade functionality
"""

import os
import sys
import uuid

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
from modules.points.models import PointsBalance

def test_membership_upgrade():
    """Test upgrading a user's membership plan"""

    db = SessionLocal()
    service = UserIntegrationService(db)
    try:
        # Get available plans
        plans = db.query(MembershipPlan).limit(2).all()
        if len(plans) < 2:
            print('❌ يحتاج الأمر إلى خطتي عضوية على الأقل')
            return False

        plan1, plan2 = plans[0], plans[1]
        print(f'✅ وُجدت خطتان: {plan1.tier_name_en} و {plan2.tier_name_en}')

        # Create a test user with first plan
        user_data = {
            'email': f'upgrade_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'upgradetest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Upgrade',
            'last_name': 'Test',
            'plan_id': str(plan1.id)
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ تم إنشاء المستخدم مع {plan1.tier_name_en}')

        # Verify initial subscription
        db = SessionLocal()
        initial_sub = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).first()

        if not initial_sub:
            print('❌ لم يتم إنشاء الاشتراك الأولي')
            db.close()
            return False

        print(f'✅ الاشتراك الأولي: {initial_sub.membership_number} (Plan: {initial_sub.plan_id})')
        initial_plan_id = str(initial_sub.plan_id)

        # Check initial points
        initial_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
        initial_points = initial_balance.current_balance if initial_balance else 0
        print(f'✅ النقاط الأولية: {initial_points}')

        db.close()

        # Now upgrade to second plan
        print(f'\\n🔄 ترقية من {plan1.tier_name_en} إلى {plan2.tier_name_en}...')
        upgrade_data = {"plan_id": str(plan2.id)}

        result = service.update_user_with_membership(user_id, upgrade_data)
        print(f'✅ تمت الترقية بنجاح!')

        # Verify the upgrade
        db = SessionLocal()

        # Should still have only ONE active subscription
        active_subs = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).all()

        if len(active_subs) != 1:
            print(f'❌ عدد الاشتراكات النشطة: {len(active_subs)} (متوقع: 1)')
            db.close()
            return False

        upgraded_sub = active_subs[0]
        print(f'✅ الاشتراك المحدث: {upgraded_sub.membership_number}')

        # Verify plan was updated
        if str(upgraded_sub.plan_id) != str(plan2.id):
            print(f'❌ خطة الاشتراك: {upgraded_sub.plan_id} (متوقع: {plan2.id})')
            db.close()
            return False

        # Verify previous_plan_id was set
        if str(upgraded_sub.previous_plan_id) != initial_plan_id:
            print(f'❌ الخطة السابقة: {upgraded_sub.previous_plan_id} (متوقع: {initial_plan_id})')
            db.close()
            return False

        # Verify upgraded_at was set
        if upgraded_sub.upgraded_at is None:
            print('❌ لم يتم تعيين تاريخ الترقية')
            db.close()
            return False

        # Verify membership number was updated
        if upgraded_sub.membership_number == initial_sub.membership_number:
            print('❌ لم يتم تحديث رقم العضوية')
            db.close()
            return False

        # Verify points were updated
        final_balance = db.query(PointsBalance).filter(PointsBalance.user_id == user_id).first()
        final_points = final_balance.current_balance if final_balance else 0

        expected_additional_points = 0
        if plan2.perks:
            perks = plan2.perks
            if isinstance(perks, str):
                import json
                perks = json.loads(perks)
            expected_additional_points = perks.get('points', 0) if isinstance(perks, dict) else 0

        expected_total_points = initial_points + expected_additional_points

        print(f'✅ النقاط قبل الترقية: {initial_points}')
        print(f'✅ النقاط المضافة: {expected_additional_points}')
        print(f'✅ النقاط النهائية: {final_points} (متوقع: {expected_total_points})')

        if final_points != expected_total_points:
            print(f'❌ النقاط غير صحيحة: {final_points} ≠ {expected_total_points}')
            db.close()
            return False

        # Verify no duplicate subscriptions
        all_user_subs = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id)
        ).all()

        active_count = sum(1 for sub in all_user_subs if sub.status == MembershipStatus.ACTIVE)
        cancelled_count = sum(1 for sub in all_user_subs if sub.status == MembershipStatus.CANCELLED)

        print(f'✅ عدد الاشتراكات النشطة: {active_count}')
        print(f'✅ عدد الاشتراكات الملغية: {cancelled_count}')

        if active_count != 1:
            print('❌ يجب أن يكون هناك اشتراك نشط واحد فقط')
            db.close()
            return False

        db.close()

        print('🎉 اختبار الترقية نجح بالكامل!')
        print('✅ تم التحديث بدلاً من الإدراج')
        print('✅ لم يحدث انتهاك للقيد الفريد')
        print('✅ تم تحديث جميع البيانات بشكل صحيح')

        return True

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_membership_upgrade()
    print(f'\\n🎯 النتيجة النهائية: {"نجح" if success else "فشل"}')
    sys.exit(0 if success else 1)
