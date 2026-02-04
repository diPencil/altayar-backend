#!/usr/bin/env python3
"""
Test script for membership update functionality
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
from modules.users.models import User

print('🧪 اختبار تحديث العضوية للمستخدمين')

def test_membership_update():
    """Test updating membership for existing user"""

    db = SessionLocal()
    try:
        service = UserIntegrationService(db)

        # Get available plans
        plans = db.query(MembershipPlan).limit(2).all()
        if len(plans) < 2:
            print('❌ يحتاج الأمر إلى خطتي عضوية على الأقل')
            return False

        plan1, plan2 = plans[0], plans[1]
        print(f'✅ وُجدت خطتان: {plan1.tier_name_en}, {plan2.tier_name_en}')

        # Create a test user without membership first
        user_data = {
            'email': f'update_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'updatetest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'Update'
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ تم إنشاء المستخدم: {result["user"]["email"]}')

        # Assign first plan
        update_data = {"plan_id": str(plan1.id)}
        result1 = service.update_user_with_membership(user_id, update_data)
        print(f'✅ تم تعيين الخطة الأولى: {plan1.tier_name_en}')

        # Verify subscription exists
        sub1 = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).first()

        if not sub1:
            print('❌ لم يتم إنشاء الاشتراك الأول')
            return False

        print(f'✅ تم إنشاء الاشتراك: {sub1.membership_number}')

        # Now update to second plan (this should update, not create new)
        update_data = {"plan_id": str(plan2.id)}
        result2 = service.update_user_with_membership(user_id, update_data)
        print(f'✅ تم تحديث الخطة إلى: {plan2.tier_name_en}')

        # Verify old subscription is cancelled
        cancelled_sub = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.CANCELLED
        ).first()

        if not cancelled_sub:
            print('❌ لم يتم إلغاء الاشتراك القديم')
            return False

        # Verify new subscription exists
        sub2 = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.ACTIVE
        ).first()

        if not sub2:
            print('❌ لم يتم إنشاء الاشتراك الجديد')
            return False

        if str(sub2.plan_id) != str(plan2.id):
            print('❌ الاشتراك الجديد لا يحتوي على الخطة الصحيحة')
            return False

        # Check that previous_plan_id is set correctly
        if sub2.previous_plan_id != plan1.id:
            print('❌ لم يتم تعيين previous_plan_id بشكل صحيح')
            return False

        if sub2.upgraded_at is None:
            print('❌ لم يتم تعيين upgraded_at')
            return False

        print(f'✅ تم إنشاء الاشتراك الجديد: {sub2.membership_number}')
        print(f'✅ تم إلغاء الاشتراك القديم: {cancelled_sub.membership_number}')
        print(f'✅ تم تعيين previous_plan_id: {sub2.previous_plan_id}')
        print(f'✅ تم تعيين upgraded_at: {sub2.upgraded_at}')

        # Test removing membership
        update_data = {"plan_id": None}
        result3 = service.update_user_with_membership(user_id, update_data)
        print('✅ تم إلغاء العضوية')

        # Verify subscription is cancelled
        cancelled_sub2 = db.query(MembershipSubscription).filter(
            MembershipSubscription.user_id == uuid.UUID(user_id),
            MembershipSubscription.status == MembershipStatus.CANCELLED
        ).all()

        if len(cancelled_sub2) != 2:
            print('❌ لم يتم إلغاء جميع الاشتراكات')
            return False

        print('✅ تم إلغاء جميع الاشتراكات')

        print('🎉 جميع اختبارات تحديث العضوية نجحت!')
        return True

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_membership_update()
    sys.exit(0 if success else 1)
