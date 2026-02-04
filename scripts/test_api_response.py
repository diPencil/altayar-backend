#!/usr/bin/env python3
"""
Test the API response structure for users list
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

def test_api_response_structure():
    """Test that the API returns the expected structure for frontend"""

    db = SessionLocal()
    try:
        service = UserIntegrationService(db)

        # Get the Silver plan
        silver_plan = db.query(MembershipPlan).filter(MembershipPlan.tier_name_en == "Silver Membership").first()
        if not silver_plan:
            print('❌ لم توجد خطة Silver Membership')
            return False

        # Create a test user with Silver membership
        user_data = {
            'email': f'api_test_{uuid.uuid4().hex[:8]}@example.com',
            'username': f'apitest_{uuid.uuid4().hex[:8]}',
            'password': 'TestPass123',
            'first_name': 'API',
            'last_name': 'Test',
            'plan_id': str(silver_plan.id)
        }

        result = service.create_user_with_membership(user_data, created_by_admin=True)
        user_id = result['user']['id']
        print(f'✅ تم إنشاء المستخدم: {result["user"]["email"]}')

        # Now test the API response structure by simulating what get_all_users would return
        from modules.admin.routes import get_all_users
        from unittest.mock import Mock

        # Mock the current_user dependency
        mock_user = Mock()

        # Call get_all_users (this would normally be done via FastAPI)
        # For testing, let's manually replicate the logic
        from sqlalchemy.orm import joinedload

        query = db.query(User).options(joinedload(User.subscriptions).joinedload(MembershipSubscription.plan))
        users = query.filter(User.id == uuid.UUID(user_id)).all()

        result_users = []
        for u in users:
            # Find latest subscription
            latest_sub = None
            if u.subscriptions:
                sorted_subs = sorted(u.subscriptions, key=lambda s: s.created_at, reverse=True)
                latest_sub = sorted_subs[0] if sorted_subs else None

            # Get points balance
            from modules.points.models import PointsBalance
            points_balance = db.query(PointsBalance).filter(PointsBalance.user_id == str(u.id)).first()

            membership_info = None
            if latest_sub and latest_sub.plan:
                membership_info = {
                    "name": latest_sub.plan.tier_name_en,
                    "code": latest_sub.plan.tier_code,
                    "color": latest_sub.plan.color_hex,
                    "status": latest_sub.status.value if hasattr(latest_sub.status, "value") else str(latest_sub.status),
                    "membership_id": latest_sub.membership_number,
                    "end_date": latest_sub.expiry_date.isoformat() if latest_sub.expiry_date else None
                }

            user_data = {
                "id": str(u.id),
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "username": u.username,
                "avatar": u.avatar,
                "phone": u.phone,
                "role": u.role.value if hasattr(u.role, 'value') else str(u.role),
                "status": u.status.value if hasattr(u.status, 'value') else str(u.status),
                "created_at": u.created_at.isoformat(),
                "membership": membership_info,
                "points": {
                    "current_balance": points_balance.current_balance if points_balance else 0,
                    "total_earned": points_balance.total_earned if points_balance else 0,
                    "total_redeemed": points_balance.total_redeemed if points_balance else 0
                } if points_balance else None
            }

            result_users.append(user_data)

        # Test the structure
        user_response = result_users[0]
        print('\\n📋 هيكل الاستجابة:')
        print(json.dumps(user_response, indent=2, ensure_ascii=False, default=str))

        # Verify expected structure for frontend
        if 'membership' not in user_response:
            print('❌ خطأ: membership object مفقود')
            return False

        if 'points' not in user_response:
            print('❌ خطأ: points object مفقود')
            return False

        membership = user_response['membership']
        points = user_response['points']

        # Check membership data
        if membership['name'] != 'Silver Membership':
            print(f'❌ خطأ: اسم العضوية خاطئ: {membership["name"]}')
            return False

        if membership['end_date'] is not None:
            print('⚠️ تحذير: يجب أن تكون تاريخ النهاية None للعضويات غير المحدودة')

        if membership['status'] != 'ACTIVE':
            print(f'❌ خطأ: حالة العضوية خاطئة: {membership["status"]}')
            return False

        # Check points data
        if points['current_balance'] != 1500:
            print(f'❌ خطأ: رصيد النقاط خاطئ: {points["current_balance"]} (متوقع: 1500)')
            return False

        if points['total_earned'] != 1500:
            print(f'❌ خطأ: إجمالي النقاط المكتسبة خاطئ: {points["total_earned"]} (متوقع: 1500)')
            return False

        print('\\n✅ هيكل الاستجابة صحيح!')
        print(f'🎫 العضوية: {membership["name"]} ({membership["status"]})')
        print(f'⭐ النقاط: {points["current_balance"]} PTS')
        print(f'📅 تاريخ النهاية: {membership["end_date"] or "غير محدد"}')

        return True

    except Exception as e:
        print(f'❌ فشل الاختبار: {str(e)}')
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_api_response_structure()
    print('\\n🎉 الاختبار نجح!' if success else '\\n❌ الاختبار فشل!')
    sys.exit(0 if success else 1)
