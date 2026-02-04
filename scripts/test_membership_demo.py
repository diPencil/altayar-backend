#!/usr/bin/env python3
"""
عرض توضيحي لإنشاء مستخدم مع عضوية
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
from modules.memberships.models import MembershipPlan

print('🧪 عرض توضيحي: إنشاء مستخدم مع عضوية')

db = SessionLocal()
try:
    service = UserIntegrationService(db)

    # احصل على خطة عضوية متاحة
    plan = db.query(MembershipPlan).first()
    if plan:
        print(f'✅ وُجدت خطة عضوية: {plan.tier_name_en}')

        # إنشاء مستخدم مع عضوية
        user_data = {
            'email': f'test_member_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'member_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'أحمد',
            'last_name': 'محمد',
            'plan_id': str(plan.id)  # هنا نحدد الخطة
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)

        print('🎉 تم إنشاء المستخدم بنجاح!')
        print(f'📧 البريد الإلكتروني: {result["user"]["email"]}')
        print(f'👤 الاسم: {result["user"]["name"]}')
        print(f'🎫 العضوية: {result["user"]["plan"]["name"] if result["user"].get("plan") else "لا توجد عضوية"}')
        print(f'⭐ النقاط الممنوحة: {result.get("points_awarded", 0)}')

        print('\n✅ في البروفايل سيظهر:')
        print('- اسم العضوية')
        print('- حالة العضوية (ACTIVE)')
        print('- رصيد النقاط')
        print('- تاريخ انتهاء العضوية')

        print('\n📱 في التطبيق:')
        print('- سيظهر المستخدم في قائمة المستخدمين مع العضوية')
        print('- في صفحة العضويات ستزيد عدد الأعضاء')
        print('- المستخدم يمكنه رؤية عضويته ونقاطه')

    else:
        print('⚠️ لم توجد خطط عضوية في النظام')

except Exception as e:
    print(f'❌ خطأ: {str(e)}')
    import traceback
    traceback.print_exc()
finally:
    db.close()
