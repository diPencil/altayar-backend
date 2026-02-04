#!/usr/bin/env python3
"""
Simple test for membership update fix
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

print('🧪 اختبار بسيط لإصلاح تحديث العضوية')

def test_simple_update():
    """Simple test for membership update"""

    # Create a new session for this test
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
            'email': f'simple_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'simpletest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'Simple',
            'last_name': 'Test'
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ تم إنشاء المستخدم: {result["user"]["email"]}')

        # Test the critical fix: updating membership
        print('🔧 اختبار التحديث الحرج: تغيير العضوية')
        update_data = {"plan_id": str(plan1.id)}

        try:
            result1 = service.update_user_with_membership(user_id, update_data)
            print(f'✅ تم تحديث العضوية بنجاح: {plan1.tier_name_en}')
            return True
        except Exception as e:
            print(f'❌ فشل تحديث العضوية: {str(e)}')
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_simple_update()
    print('🎉 الاختبار نجح!' if success else '❌ الاختبار فشل!')
    sys.exit(0 if success else 1)
